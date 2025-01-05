import re

def monitor_inbox(user_code):
    # This is a dummy implementation. In a real scenario, this would
    # interact with social media APIs to fetch messages.
    
    # Read from a dummy file for now
    try:
        with open('dummy_inbox.txt', 'r') as f:
            inbox_content = f.read()
    except FileNotFoundError:
        return []

    messages = []
    message_pattern = re.compile(rf'{user_code}\s+(https?://\S+)')
    for line in inbox_content.splitlines():
        match = message_pattern.search(line)
        if match:
            messages.append(match.group(1))
    return messages

if __name__ == '__main__':
    # Example usage
    user_code = "user123"
    messages = monitor_inbox(user_code)
    if messages:
        print(f"Found messages for user {user_code}:")
        for message in messages:
            print(message)
    else:
        print(f"No messages found for user {user_code}")
