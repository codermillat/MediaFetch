#!/bin/zsh

# Messenger API Webhook Setup Script

# Variables
VERIFY_TOKEN="my_verify_token_123"
CALLBACK_URL="https://myserver.com/webhook"
PAGE_ACCESS_TOKEN="your_page_access_token_here"
APP_ID="your_app_id_here"

# Function to setup webhook
setup_webhook() {
  curl -X POST "https://graph.facebook.com/v15.0/$APP_ID/subscriptions" \
  -H "Content-Type: application/json" \
  -d '{
    "object": "page",
    "callback_url": "'"$CALLBACK_URL"'",
    "fields": [
      "messages",
      "messaging_postbacks",
      "messaging_optins",
      "messaging_referrals",
      "messaging_handovers",
      "messaging_policy_enforcement",
      "messaging_payments",
      "messaging_checkout_updates",
      "messaging_pre_checkouts",
      "messaging_delivery",
      "messaging_read",
      "messaging_account_linking"
    ],
    "verify_token": "'"$VERIFY_TOKEN"'",
    "include_values": true
  }'
}

# Check if PAGE_ACCESS_TOKEN and APP_ID are set
if [ -z "$PAGE_ACCESS_TOKEN" ] || [ -z "$APP_ID" ]; then
  echo "Please set PAGE_ACCESS_TOKEN and APP_ID in the script."
  exit 1
fi

# Call the function
setup_webhook
