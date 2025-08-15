# Instagram Integration Setup Guide

This guide explains how to set up Instagram integration with your MediaFetch bot to fetch messages, posts, and stories from Instagram accounts.

## 🔑 Prerequisites

1. **Instagram Account**: You need an Instagram account
2. **Facebook Developer Account**: Required for API access
3. **Instagram Basic Display App**: To get access tokens
4. **Heroku App**: Your MediaFetch bot deployed on Heroku

## 📱 Step-by-Step Setup

### Step 1: Create Facebook Developer Account

1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Click "Get Started" and log in with your Facebook account
3. Complete the developer verification process if required

### Step 2: Create Instagram Basic Display App

1. In your Facebook Developer Console, click "Create App"
2. Choose "Consumer" as the app type
3. Fill in your app details:
   - **App Name**: MediaFetch Bot
   - **App Contact Email**: Your email
   - **App Purpose**: Personal project
4. Click "Create App"

### Step 3: Add Instagram Basic Display Product

1. In your app dashboard, click "Add Product"
2. Find "Instagram Basic Display" and click "Set Up"
3. You'll see a setup wizard - follow the steps

### Step 4: Configure Instagram Basic Display

1. **Basic Display** section:
   - **Client OAuth Settings**:
     - Valid OAuth Redirect URIs: Add your Heroku app URL (e.g., `https://your-app.herokuapp.com/auth/instagram/callback`)
     - Deauthorize Callback URL: Same as above
     - Data Deletion Request URL: Same as above
   
2. **Instagram Basic Display** section:
   - **Instagram App ID**: Note this down
   - **Instagram App Secret**: Note this down (keep it secret!)

### Step 5: Generate Instagram Access Token

1. In your app dashboard, go to "Instagram Basic Display" → "Basic Display"
2. Click "Generate Token"
3. You'll be redirected to Instagram to authorize your app
4. Grant the requested permissions
5. Copy the generated access token

### Step 6: Set Environment Variables

Set the Instagram access token in your Heroku app:

```bash
heroku config:set INSTAGRAM_ACCESS_TOKEN="your_access_token_here"
```

Or set it in your local `.env` file:

```bash
INSTAGRAM_ACCESS_TOKEN=your_access_token_here
```

## 🚀 Using Instagram Features

Once configured, you can use these commands:

### Basic Instagram Commands

- `/instagram profile [username]` - Get account profile
- `/instagram media [username] [limit]` - Get recent media posts
- `/instagram stories [username]` - Get stories
- `/instagram insights [username]` - Get account insights

### Monitoring Commands

- `/monitor [username]` - Start monitoring an account
- `/monitor list` - List monitored accounts
- `/monitor check` - Check for new content
- `/unmonitor [username]` - Stop monitoring

## 📊 What You Can Access

### Available Data (Instagram Basic Display API)

✅ **Available:**
- Your own profile information
- Your own media posts
- Your own stories
- Public account profiles (if they allow it)
- Public media from accounts you follow

❌ **Not Available:**
- Direct messages
- Private account content
- Comments on posts
- Likes and engagement metrics
- Business insights (requires Business API)

### Example Usage

```
# Get your own profile
/instagram profile me

# Get recent posts from a public account
/instagram media instagram 10

# Monitor an account for new content
/monitor instagram

# Check for new content
/monitor check
```

## 🔒 Security & Privacy

### Important Notes

1. **Access Token Security**: Never share your access token
2. **Rate Limits**: Instagram has API rate limits
3. **Permissions**: Only request permissions you need
4. **Data Usage**: Respect user privacy and Instagram's terms

### Token Expiration

Instagram access tokens can expire. To refresh:

1. Go to your Facebook Developer Console
2. Navigate to Instagram Basic Display
3. Generate a new token
4. Update your Heroku config

## 🐛 Troubleshooting

### Common Issues

1. **"Instagram integration not configured"**
   - Check if `INSTAGRAM_ACCESS_TOKEN` is set
   - Verify the token is valid

2. **"Account not found or inaccessible"**
   - Account might be private
   - You might not have permission to access it
   - Check if the username is correct

3. **"API request failed"**
   - Token might be expired
   - Rate limit exceeded
   - Check Instagram API status

### Debug Commands

```bash
# Check Heroku config
heroku config

# View logs
heroku logs --tail

# Check Instagram token info
# Use /instagram command in the bot
```

## 📈 Advanced Features

### Monitoring Multiple Accounts

You can monitor multiple Instagram accounts:

```
/monitor account1
/monitor account2
/monitor account3
/monitor list
/monitor check
```

### Content Filtering

The bot automatically:
- Tracks new content since last check
- Provides summaries of content
- Extracts media URLs for downloading
- Formats information for easy reading

## 🔄 Alternative Approaches

### If Basic Display API is Limited

1. **Instagram Graph API**: For business accounts
2. **Third-party Services**: Like RapidAPI Instagram endpoints
3. **Web Scraping**: Not recommended (against ToS)

### Business Account Integration

If you have a business Instagram account:

1. Connect it to a Facebook Page
2. Use Instagram Graph API instead
3. Get more comprehensive data access

## 📚 Resources

- [Instagram Basic Display API Documentation](https://developers.facebook.com/docs/instagram-basic-display-api)
- [Facebook Developer Documentation](https://developers.facebook.com/)
- [Instagram Platform Policies](https://developers.facebook.com/docs/instagram-platform-policy)
- [API Rate Limits](https://developers.facebook.com/docs/graph-api/overview/rate-limiting)

## 🆘 Support

If you encounter issues:

1. Check this guide first
2. Review Instagram API documentation
3. Check your Facebook Developer Console
4. Verify your access token
5. Check Heroku logs for errors

---

**Note**: Instagram's API policies and features may change. Always refer to the official documentation for the most up-to-date information.
