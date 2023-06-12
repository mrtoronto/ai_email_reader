## Overview

This script is meant to help people clean out their gmail inboxes. 

The LLM will go through your inbox deciding whether emails require action or whether they can be safely marked as seen.

This happens in two phases.
- Phase 1
    - As the LLM labels emails, each example is manually checked by the human and saved where the human specifies. 
    - After a certain number of examples, the LLM generates a summary of the labeling preferences for both the MARK AS SEEN and ACTION REQUIRED labels.
    - These summaries are given to the model when labelling so eventually it should learn what you want.

- Phase 2
    - The LLM labels emails unsupervised. It uses the preference summaries generated during phase 1 to guide its decisions
    - This phase does not require human intervention. 

Email labels are generated using GPT-3.5 while the labeling preference summaries are generated using GPT-4.

### Phase 1 details

Each email is presented to the user along with the models label. 
- If the label is correct, reply with y or yes.
- If it is not correct, reply with n or no. 

Emails that should be marked as seen are marked as seen after the user replies with their label.

Every 5 emails, the LLM will generate a summary of the labeling preferences for both the MARK AS SEEN and ACTION REQUIRED labels.
- The value 5 can be changed with the `N_EMAILS_PER_SUMMARY` variable in `main.py`

### Phase 2 details

The LLM will label emails unsupervised. It uses the preference summaries generated during phase 1 to guide its decisions.

You shouldn't have to pay attention during this step but I would watch the console bc you can't trust the robots yet.

## Setup

Clone the repo, setup a venv, create your own local_settings.py file then run the code.

```
git clone https://github.com/mrtoronto/ai_email_reader.git
cd ai_email_reader
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## App passwords

You can't log into a gmail account from a third-party app using your normal password. You'll need to go to the link below (or find google app passwords on a search engine) and set one up.

The result will be a 12 character string you can use in place of your password. 

https://support.google.com/accounts/answer/185833?hl=en&sjid=17233954404880666546-NA



## Conclusions

TL;DR: this is not a very effective method for cleaning your inbox. 

It is slightly more effective than marking everything as read but its a lot more work, has a non-zero cost and isn't perfect. 

## Future directions
- Add support for other mailboxes
- Improve the summary generation by:
    - improving the prompt
    - Use adversarial examples more effectively
        - Example: Model thought email 1 was a MARK AS SEEN email but its actually action required. This example is more valuable than an example the model already knew the answer to. 
    - Do a better job filtering similar examples
        - Levenshtein distance is good but not perfect
- Come up with a more complex method of letting AI generate rules
    - Instead of describing the rules, AI could output traditional filter logic where relevant
- Incorporate email body's
    - Not usually necessary but maybe helpful
    - Does make it much harder to fit many examples in a single prompt for summary generation
- UI
    - This is a command line tool. It could be a web app. 
    - This would make it easier to use and easier to share with others
    - I don't want to do it
- Pre-AI logic
    - There's a lot that could be done with simpler methods
    - Look for addresses with TONS of unread emails and unread all of their emails without checking
        - Looking at you facebook.
    - Look for common trends in subjects and unread all of those
    - This is all technically "easy" but difficult to do conveniently without a UI


## Limitations
- GPT-4 still kinda sucks at generating concise sets of guidelines without overfitting or including irrelevant information
    - This is important bc the rules for what should be marked as seen and what needs action are nuanced but not complicated.
    - Maybe with the right mix of examples, it could generate a good summary but its tough to tell what's good enough to let it run unsupervised