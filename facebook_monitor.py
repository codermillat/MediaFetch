import requests

FACEBOOK_PAGE_ACCESS_TOKEN = 'FACEBOOK_PAGE_ACCESS_TOKEN'

def get_recent_messages():
    url = f'https://graph.facebook.com/v15.0/me/messages?access_token={FACEBOOK_PAGE_ACCESS_TOKEN}'
    response = requests.get(url)
    return response.json()

def process_messages(messages, unique_code):
    for entry in messages['entry']:
        for message_event in entry['messaging']:
            text = message_event['message']['text']
            if unique_code in text:
                link = text.split(unique_code)[-1].strip()
                return link
    return None
