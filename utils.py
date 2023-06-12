
import Levenshtein
from collections import defaultdict
import imaplib
import email
from email.header import decode_header

from local_settings import EMAIL, APP_PASSWORD


def get_mail():
    # Authenticate and select the mailbox
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(EMAIL, APP_PASSWORD)
    mail.select("inbox")
    return mail

def get_unseen_emails(mail):

    # Search for unread emails
    _, msgnums = mail.search(None, "UNSEEN")
    msgnums = msgnums[0].split()

    return msgnums

def count_agg_unseen_emails(mail, msgnums):
    senders_count = defaultdict(int)
    subjects_count = defaultdict(int)

    for num in msgnums:
        _, msg_data = mail.fetch(num, "(BODY.PEEK[])")
        
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_string(response_part[1].decode())
                email_subject = decode_header(msg["Subject"])[0][0]
                email_from = decode_header(msg["From"])[0][0]

                if isinstance(email_subject, bytes):
                    email_subject = email_subject.decode()

                if isinstance(email_from, bytes):
                    email_from = email_from.decode()

                # Count the senders and subjects
                senders_count[email_from] += 1
                subjects_count[email_subject] += 1

    print("\nSenders count:")
    for sender, count in sorted(senders_count.items(), key=lambda x: x[1], reverse=True):
        if count > 1:
            print(f"{sender}: {count}")

    print("\nSubjects count:")
    for subject, count in sorted(subjects_count.items(), key=lambda x: x[1], reverse=True):
        if count > 1:
            print(f"{subject}: {count}")

    return senders_count, subjects_count


def is_text_similar(text, previous_texts, min_similarity_ratio=0.8):
    text_subject = "\n".join(text.split("\n")[0:2])
    for previous_text in previous_texts:
        previous_text_subject = "\n".join(previous_text.split("\n")[0:2])
        similarity_ratio = Levenshtein.ratio(text_subject, previous_text_subject)
        if similarity_ratio > min_similarity_ratio: 
            return True
    return False

def make_email_text(msg, seen_examples=[], action_examples=[]):
    email_subject = decode_header(msg["Subject"])[0][0]
    email_from = decode_header(msg["From"])[0][0]
    email_date = decode_header(msg["Date"])[0][0]

    if isinstance(email_subject, bytes):
        email_subject = email_subject.decode()

    if isinstance(email_from, bytes):
        email_from = email_from.decode()
    
    if isinstance(email_date, bytes):
        email_date = email_date.decode()

    ### Skipped in phase 2
    email_text = f"Subject: {email_subject}\nFrom: {email_from}\nSent at: {email_date}"
    if seen_examples and is_text_similar(email_text, seen_examples):
        return None
    if action_examples and is_text_similar(email_text, action_examples):
        return None
    return email_text

def parse_response_to_label(response):
    response = response.lower()
    if 'action required' in response:
        return 'ACTION REQUIRED'
    elif 'mark as seen' in response:
        return 'MARK AS SEEN'
    else:
        return 'UNSURE'
