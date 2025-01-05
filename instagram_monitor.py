import requests

INSTAGRAM_ACCESS_TOKEN = 'INSTAGRAM_ACCESS_TOKEN'

def get_recent_messages():
    url = f'https://graph.instagram.com/me/messages?fields=messages{{message,from}}&access_token={INSTAGRAM_ACCESS_TOKEN}'
    response = requests.get(url)
    return response.json()

def process_messages(messages, unique_code):
    for message in messages:
        for item in message['messages']['data']:
            text = item['message']
            if unique_code in text:
                link = text.split(unique_code)[-1].strip()
                return link
    return None
