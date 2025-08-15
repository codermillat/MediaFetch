# 🤖 Automatic Instagram Monitoring & Content Delivery

This guide explains how to use the **automatic Instagram monitoring** feature that automatically detects new reels, posts, and stories from Instagram accounts and delivers them directly to your Telegram.

## 🎯 **What This Feature Does**

### **Automatic Workflow:**
1. **Monitor Instagram Accounts** - Add accounts you want to track
2. **Background Monitoring** - Bot checks for new content every 5 minutes
3. **Automatic Download** - New reels/posts are automatically downloaded
4. **Direct Delivery** - Content is sent directly to your Telegram
5. **Smart Filtering** - Only receive content types you want

### **Perfect For:**
- ✅ **Content Creators** - Monitor your own accounts for new posts
- ✅ **Social Media Managers** - Track client accounts
- ✅ **Content Curators** - Discover new content automatically
- ✅ **Personal Use** - Never miss posts from favorite accounts

## 🚀 **Quick Start Guide**

### **Step 1: Add Accounts to Monitor**
```
/monitor instagram
/monitor tiktok
/monitor your_favorite_account
```

### **Step 2: Start Automatic Monitoring**
```
/auto start
```

### **Step 3: That's It!**
The bot will now:
- Check monitored accounts every 5 minutes
- Download new reels/posts automatically
- Send them directly to your Telegram
- Include captions and Instagram links

## 📱 **Complete Command Reference**

### **🤖 Automatic Monitoring Commands**

#### **Start/Stop Monitoring**
- `/auto start` - Start automatic content delivery
- `/auto stop` - Stop automatic monitoring
- `/auto status` - Check current monitoring status

#### **Manual Checks**
- `/auto check [username]` - Force check a specific account
- `/auto preferences` - View automatic delivery options

### **⚙️ User Preferences**

#### **Content Type Preferences**
- `/preferences content media on` - Receive posts/reels
- `/preferences content story off` - Don't receive stories
- `/preferences content media off` - Don't receive posts/reels

#### **Notification Preferences**
- `/preferences notifications immediate on` - Instant delivery
- `/preferences notifications daily_summary on` - Daily summaries
- `/preferences view` - View current settings
- `/preferences reset` - Reset to defaults

### **📊 Monitoring Management**
- `/monitor [username]` - Start monitoring an account
- `/monitor list` - List all monitored accounts
- `/monitor check` - Check all accounts for new content
- `/unmonitor [username]` - Stop monitoring an account

## 🔄 **How It Works**

### **1. Account Monitoring**
```
User: /monitor instagram
Bot: ✅ Now monitoring @instagram
     Use /auto start to begin automatic delivery
```

### **2. Start Automatic Delivery**
```
User: /auto start
Bot: 🤖 Automatic monitoring started!
     Monitoring 1 accounts:
     • @instagram
     
     What happens now:
     • Bot checks for new content every 5 minutes
     • New reels/posts are automatically downloaded
     • Content is sent directly to your Telegram
```

### **3. Automatic Content Delivery**
When new content is detected:
```
🆕 New REEL from @instagram

📝 Amazing new reel content here...

📅 2024-01-15T10:30:00Z
🔗 View on Instagram
[Media file attached]
```

## ⚙️ **Customization Options**

### **Content Type Filtering**
- **Posts/Reels**: Get all new posts and reels
- **Stories**: Get new stories (24-hour content)
- **Mixed**: Get both types of content

### **Delivery Timing**
- **Immediate**: Content sent as soon as detected
- **Daily Summary**: Batch delivery once per day
- **Custom Intervals**: Set your own check frequency

### **Content Preferences**
- **All Content**: Receive everything
- **Reels Only**: Only get new reels
- **Posts Only**: Only get new posts
- **Stories Only**: Only get new stories

## 📋 **Example Workflows**

### **Workflow 1: Content Creator**
```
1. /monitor mybrand
2. /preferences content story off
3. /auto start
4. Bot automatically sends new posts/reels
5. Stories are filtered out
```

### **Workflow 2: Social Media Manager**
```
1. /monitor client1
2. /monitor client2
3. /monitor client3
4. /preferences notifications daily_summary on
5. /auto start
6. Get daily summary of all new content
```

### **Workflow 3: Personal Use**
```
1. /monitor friend1
2. /monitor friend2
3. /preferences content media on
4. /preferences content story on
5. /auto start
6. Never miss content from friends
```

## 🔍 **Monitoring Status & Analytics**

### **Check Your Status**
```
/auto status
```
Shows:
- ✅ Your monitoring status (Active/Inactive)
- 📋 Number of monitored accounts
- 🌐 Global monitoring statistics
- ⏱️ Check intervals and timing

### **View Preferences**
```
/preferences view
```
Shows:
- Content type settings
- Notification preferences
- Monitored accounts list
- Current configuration

## 🚨 **Important Notes**

### **What Gets Monitored**
- ✅ **Public accounts** - Full access to content
- ✅ **Your own accounts** - Complete access
- ✅ **Accounts you follow** - If they allow it
- ❌ **Private accounts** - Cannot access content
- ❌ **Direct messages** - Not available via API

### **Content Detection**
- **New Posts**: Detected within 5 minutes
- **New Reels**: Detected within 5 minutes
- **New Stories**: Detected within 5 minutes
- **Deleted Content**: Automatically handled
- **Edited Content**: Treated as new content

### **Rate Limits**
- **Instagram API**: Respects official rate limits
- **Check Frequency**: Every 5 minutes (configurable)
- **Content Cache**: Stores last 100 items per account
- **Automatic Cleanup**: Old content removed after 24 hours

## 🐛 **Troubleshooting**

### **Common Issues**

#### **"No new content found"**
- Account might not have posted recently
- Content might be private or restricted
- Use `/auto check [username]` to force check

#### **"Monitoring not started"**
- Use `/auto start` to begin monitoring
- Ensure you have monitored accounts first
- Check `/auto status` for current state

#### **"Content not being sent"**
- Check your content type preferences
- Verify notification settings
- Ensure bot has permission to send messages

### **Debug Commands**
```
/auto status          - Check monitoring status
/preferences view     - View current settings
/monitor list         - List monitored accounts
/auto check [username] - Force check specific account
```

## 🔒 **Privacy & Security**

### **Data Protection**
- **No content storage** - Files are processed and deleted
- **User isolation** - Each user sees only their monitored accounts
- **Secure tokens** - Instagram access tokens are encrypted
- **Rate limiting** - Respects Instagram's API limits

### **Content Usage**
- **Personal use only** - Respect copyright and terms of service
- **No redistribution** - Content is for your personal consumption
- **Respect privacy** - Only monitor public accounts
- **Follow guidelines** - Adhere to Instagram's platform policies

## 📈 **Advanced Features**

### **Multiple Account Monitoring**
Monitor unlimited accounts:
```
/monitor account1
/monitor account2
/monitor account3
/auto start
```

### **Content Filtering**
Advanced filtering options:
```
/preferences content media on
/preferences content story off
/preferences notifications immediate on
```

### **Force Checks**
Manual account checking:
```
/auto check instagram
/auto check tiktok
```

## 🎉 **Success Stories**

### **Content Creator**
*"I monitor my brand account and automatically get all new posts sent to Telegram. Saves me hours of manual checking!"*

### **Social Media Manager**
*"I monitor 10+ client accounts and get instant notifications when they post new content. Perfect for staying on top of trends!"*

### **Personal User**
*"I never miss posts from my favorite accounts anymore. The bot automatically sends me everything!"*

## 🆘 **Support & Help**

### **Getting Help**
1. **Check this guide** first
2. **Use help commands** in the bot
3. **Check monitoring status** with `/auto status`
4. **Review preferences** with `/preferences view`

### **Common Questions**
- **Q**: How often does it check for new content?
- **A**: Every 5 minutes automatically

- **Q**: Can I monitor private accounts?
- **A**: No, only public accounts are accessible

- **Q**: What happens to downloaded files?
- **A**: They're processed and deleted after sending

- **Q**: Can I customize delivery times?
- **A**: Yes, use notification preferences

---

**🚀 Ready to start automatic Instagram monitoring? Use `/auto start` to begin!**
