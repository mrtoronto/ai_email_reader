import json
import random
import time
import openai
import email

from local_settings import OAI_API_KEY
from utils import get_mail, get_unseen_emails, make_email_text, parse_response_to_label
from constants import (
    N_TRUNC,
    N_EMAILS_PER_SUMMARY,
    PHASE_1_MAX_SEEN_EXAMPLES,
    PHASE_1_MIN_ACTION_EXAMPLES
)

openai.api_key = OAI_API_KEY

def call_chatgpt_phase_1(email_text, seen_prompt, action_prompt):
    prompt = [
        {
            "role": "system",
            "content": f"""You are a bot that can detect if an email needs action or is not important. You do this in a 2 stage evaluation process. This is the first stage. 
            
The first stage is done a few emails at a time to let the human calibrate the system. During the first stage, you will be asked to update your custom prompt for the user. This will let you learn and remember the users preferences.
The second stage is done unsupervised on their whole inbox using the refined custom prompt.
"""
        },
        {
            "role": "system", 
            "content": f"""
You will be provided with an email, its sender, subject and the beginning of its body text. Your goal is to decide whether it needs action or not. Do not respond with any text other than ACTION REQUIRED or MARK AS SEEN.
            
If it needs action, you should respond with ACTION REQUIRED. 
If it does not need action, you should respond with MARK AS SEEN.

Do not respond with any text other than ACTION REQUIRED or MARK AS SEEN.
            """
        },
        {
            "role": "system",
            "content": f"""
The current user's preference prompt for MARK AS SEEN emails:
{seen_prompt}
            """
        },
        {
            "role": "system",
            "content": f"""
The current user's preference prompt for ACTION REQUIRED emails:
{action_prompt}
            """
        },
        {
            "role": "user", 
            "content": email_text
        },
    ]
    try:
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=prompt,
        )
    except:
        time.sleep(2)
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=prompt,
        )
    return completion.choices[0].message['content'], completion.usage['total_tokens']

def refine_action_preference_prompt(action_prompt, action_examples, seen_examples):
    seen_examples_str = "\n".join(seen_examples)
    action_examples_str = "\n".join(action_examples)
    prompt = [
        {
            "role": "system", 
            "content": f"""You are a bot that summarizes email labeling rules for other language models. You are creating guidelines and suggestions for another bot that will mark emails as ACTION REQUIRED. 
            
You will be provided with several examples of emails the user wants to interact with after the inbox cleaning is complete. Your goal is to update the provided preferences prompt so other models can label emails better using these instructions. If the provided prompt is empty, that means one hasn't been created yet. In this case, just say None.
            
Only return your description of the users preferences as a concise bulleted list. 
Make sure the rules are general enough to apply across the whole inbox and not overfit on specific emails.
Do not return the examples or any other text.
"""
        },
        {
            "role": "system",
            "content": f"""
The current user's preference prompt for emails that require action is:
{action_prompt}
            """
        },
        {
            "role": "system",
            "content": f"""
These are examples of emails that the user wants to take action on. Learn the patterns in these and refine your custom prompt. 
{action_examples_str}
            """
        },
        {
            "role": "system",
            "content": f"""
These are examples of emails that the user wants to mark as seen. Learn the patterns in these and avoid including them in your prompt. 
{seen_examples_str}
            """
        },
    ]
    prompt += [
        {
            "role": "assistant",
            "content": "Updated ACTION REQUIRED preferences prompt:"
        }
    ]

    try:
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=prompt,
            max_tokens=500,
        )
    except:
        time.sleep(2)
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=prompt,
            max_tokens=500,
        )

    return completion.choices[0].message['content'], completion.usage['total_tokens'] * 10

def refine_seen_preference_prompt(seen_prompt, seen_examples, action_examples):
    seen_examples_str = "\n".join(seen_examples)
    action_examples_str = "\n".join(action_examples)
    prompt = [
        {
            "role": "system", 
            "content": f"""You are a bot that summarizes email labeling rules for other language models. You are creating the guidelines and suggestions for another bot that will mark emails as MARK AS SEEN. 
            
You will be provided with several examples of emails the user wants to mark as seen while cleaning their inbox. Your goal is to update the provided preferences prompt so models can label emails better using these instructions. If the provided prompt is empty, that means one hasn't been created yet. In this case, just say None.
            
Only return your description of the users preferences as a concise bulleted list. 
Make sure the rules are general enough to apply across the whole inbox and not overfit on specific emails.
Do not return the examples or any other text.
"""
        },
        {
            "role": "system",
            "content": f"""
The current user's preference prompt for emails that should be marked as seen is:
{seen_prompt}
"""
        },
        {
            "role": "system",
            "content": f"""
These are examples of emails that the user wants to mark as seen. Learn the patterns in these and refine your custom prompt. 
{seen_examples_str}
"""
        },
        {
            "role": "system",
            "content": f"""
These are examples of emails that the user wants to mark as action required. Learn the patterns in these and avoid including them in your prompt. 
{action_examples_str}
"""
        },
    ]
    prompt += [
        {
            "role": "assistant",
            "content": "Updated MARK AS SEEN preferences prompt:"
        }
    ]

    try:
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=prompt,
            max_tokens=500,
        )
    except:
        time.sleep(2)
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=prompt,
            max_tokens=500,
        )

    return completion.choices[0].message['content'], completion.usage['total_tokens'] * 10

def call_chatgpt_phase_3(email_text, action_prompt, seen_prompt):
    prompt = [
        {
            "role": "system", 
            "content": f"""You are a bot that can detect if an email needs action or is not important. You do this in a 2 stage evaluation process. This is the second stage. 
            
The first stage is done a few emails at a time to let the human calibrate the system. During the first stage, you will be asked to update your custom prompt for the user. This will let you learn and remember the users preferences.
The second stage is done unsupervised on their whole inbox using the refined custom preference prompt.
            
In this stage, the human will not see each action you take so if you are unsure about an email, you should respond with UNSURE.
            
You will be provided with a few successful examples from the first phase to use as guidence. 
            
You will also be provided with an email, its sender, subject and the beginning of its body text. Your goal is to decide whether it needs action or not.
            
If it needs action, you should respond with ACTION REQUIRED. 
If it does not need action, you should respond with MARK AS SEEN.
If you do not know, respond with UNSURE.
"""
        },
        {
            "role": "system",
            "content": f"""
The current user's preference prompt for MARK AS SEEN emails:
{seen_prompt}
"""
        },
        {
            "role": "system",
            "content": f"""
The current user's preference prompt for ACTION REQUIRED emails:
{action_prompt}
"""
        },
    ]

    prompt += [
        {
            "role": "user", 
            "content": email_text
        },
    ]
    
    try:
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=prompt,
        )
    except:
        time.sleep(2)
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=prompt,
        )
    return completion.choices[0].message["content"], completion.usage['total_tokens']


def phase_1(mail, msgnums, token_usage, n_samples=100):
    random_msg_idxs = random.sample(msgnums, n_samples)

    print(f'\n\n####### Phase 1 LLM parsing after {time.time() - start_time:.2f} seconds\n\n')

    ### Phase 1
    ### Successful examples necessary to pass phase 1
    seen_examples = []
    action_examples = []
    seen_prompt = 'I should label emails the user does not need as MARK AS SEEN'
    action_prompt = 'I should label emails the user does need as ACTION REQUIRED'
    num_idx = 0

    for num in random_msg_idxs:
        _, msg_data = mail.fetch(num, "(BODY.PEEK[])")

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_string(response_part[1].decode())
                email_text = make_email_text(msg, seen_examples=seen_examples, action_examples=action_examples)

                ### Sender was too similar to previous senders
                if not email_text:
                    continue
                
                gpt_response, tokens_used = call_chatgpt_phase_1(email_text, seen_prompt, action_prompt)
                token_usage += tokens_used

                label = parse_response_to_label(gpt_response)

                if label == 'MARK AS SEEN' and len(seen_examples) >= PHASE_1_MAX_SEEN_EXAMPLES:
                    print(f'Skipping MARK AS SEEN example because we already have {PHASE_1_MAX_SEEN_EXAMPLES} examples')
                    continue
                    
                print(f"> {label}\n{email_text}")

                user_feedback = input('Robot do good? (y/n) ')
                print()

                if user_feedback.lower().strip() in ['y', 'yes']:
                    ### Robot did good so sort example in the right list
                    if label == 'ACTION REQUIRED':
                        action_examples.append(email_text)
                    elif label == 'MARK AS SEEN':
                        seen_examples.append(email_text)
                        mail.store(num, "+FLAGS", "\\Seen")
                elif user_feedback.lower().strip() in ['n', 'no']:
                    ### Robot did bad so sort example in the opposite list
                    if label == 'ACTION REQUIRED':
                        seen_examples.append(email_text)
                        mail.store(num, "+FLAGS", "\\Seen")
                    elif label == 'MARK AS SEEN':
                        action_examples.append(email_text)
                else:
                    print('Invalid input, skipping')
                    continue

        if user_feedback.lower() == 'end':
            print('Phase 1 ended by user')
            break
        if len(action_examples) >= PHASE_1_MIN_ACTION_EXAMPLES:
            print('Phase 1 passed with enough action examples')
            break
        
        if num_idx % N_EMAILS_PER_SUMMARY == 0:
            seen_prompt, tokens_used = refine_seen_preference_prompt(seen_prompt, seen_examples, action_examples)
            token_usage += tokens_used
            print(f'Seen prompt updated w/ {len(seen_examples)} examples to:\n{seen_prompt}\nTokens used: {tokens_used}')
            action_prompt, tokens_used = refine_action_preference_prompt(action_prompt, action_examples, seen_examples)
            token_usage += tokens_used
            print(f'Action prompt updated w/ {len(action_examples)} examples to:\n{action_prompt}\nTokens used: {tokens_used}')

        if num_idx == len(random_msg_idxs) - 1:
            print('Phase 1 ended with not enough examples')

        num_idx += 1

    seen_prompt, tokens_used = refine_seen_preference_prompt(seen_prompt, seen_examples, action_examples)
    token_usage += tokens_used
    print(f'Seen prompt updated w/ {len(seen_examples)} examples to:\n{seen_prompt}\nTokens used: {tokens_used}')
    action_prompt, tokens_used = refine_action_preference_prompt(action_prompt, action_examples, seen_examples)
    token_usage += tokens_used
    print(f'Action prompt updated w/ {len(action_examples)} examples to:\n{action_prompt}\nTokens used: {tokens_used}')

    return seen_prompt, action_prompt, token_usage


def phase_2(mail, msgnums, token_usage, seen_prompt, action_prompt):
    action_required_emails = []
    seen_emails = []
    unsure_emails = []
    if N_TRUNC:
        msgnums = msgnums[:N_TRUNC]
    for num in msgnums:
        _, msg_data = mail.fetch(num, "(BODY.PEEK[])")
        
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_string(response_part[1].decode())
                email_text = make_email_text(msg)
                
                gpt_response, tokens_used = call_chatgpt_phase_3(email_text, seen_prompt=seen_prompt, action_prompt=action_prompt)
                token_usage += tokens_used
                
                label = parse_response_to_label(gpt_response)
                    
                print(f"> {label} \n {email_text}\nTokens used: {tokens_used}")

                if label == 'ACTION REQUIRED':
                    action_required_emails.append(email_text)
                elif label == 'MARK AS SEEN':
                    seen_emails.append(email_text)
                    # mail.store(num, "+FLAGS", "\\Seen")
                elif label == 'UNSURE':
                    unsure_emails.append(email_text)

    return action_required_emails, seen_emails, unsure_emails, token_usage


############################################

if __name__ == "__main__":

    token_usage = 0

    start_time = time.time()
    mail = get_mail()
    print(f'Got mail after {time.time() - start_time:.2f} seconds')
    msgnums = get_unseen_emails(mail)
    print(len(msgnums))
    print(f'Counting after {time.time() - start_time:.2f} seconds')

    ### Phase 1
    seen_prompt, action_prompt, token_usage = phase_1(
        mail=mail, 
        msgnums=msgnums, 
        token_usage=token_usage
    )

    # count_agg_unseen_emails(mail, msgnums)

    print(f'\n\n####### Phase 2 LLM parsing after {time.time() - start_time:.2f} seconds \n\n')

    action_required_emails, seen_emails, unsure_emails, token_usage = phase_2(
        mail=mail, 
        msgnums=msgnums, 
        token_usage=token_usage, 
        seen_prompt=seen_prompt, 
        action_prompt=action_prompt
    )

    mail.close()
    mail.logout()

    with open('test_action_output.json', 'w') as f:
        json.dump(action_required_emails, f, indent=4)

    with open('test_seen_output.json', 'w') as f:
        json.dump(seen_emails, f, indent=4)

    with open('test_output_logs.json', 'w') as f:
        json.dump({
            'seen_prompt': seen_prompt,
            'action_prompt': action_prompt,
            'total_tokens_used': token_usage,
            'total_tokens_used_usd': (token_usage / 1000) * 0.003,
            'action_required_emails': len(action_required_emails),
            'seen_emails': len(seen_emails),
            'unsure_emails': len(unsure_emails),
            'total_emails': len(action_required_emails) + len(seen_emails) + len(unsure_emails),
        }, f, indent=4)

    print("Total tokens used:", token_usage)