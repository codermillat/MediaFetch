# 🚀 MediaFetch Production Deployment Guide

## 📋 Prerequisites

- [Heroku Account](https://signup.heroku.com/)
- [GitHub Account](https://github.com/)
- [Telegram Bot Token](https://t.me/BotFather)
- [Supabase Project](https://supabase.com/)

## 🔧 Heroku Setup

### 1. Create Heroku App

```bash
# Install Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Login to Heroku
heroku login

# Create new app
heroku create your-mediafetch-app-name

# Set buildpack for Python
heroku buildpacks:set heroku/python

# Add FFmpeg buildpack
heroku buildpacks:add https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git
```

### 2. Configure Environment Variables

```bash
# Set production environment
heroku config:set ENVIRONMENT=production
heroku config:set FLASK_ENV=production
heroku config:set FLASK_DEBUG=false

# Set Telegram bot token
heroku config:set TELEGRAM_BOT_TOKEN=your_bot_token_here

# Set Supabase credentials
heroku config:set SUPABASE_URL=https://your-project.supabase.co
heroku config:set SUPABASE_ANON_KEY=your_anon_key
heroku config:set SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Set Instagram credentials
heroku config:set INSTAGRAM_USERNAME=mediafetchbot
heroku config:set INSTAGRAM_PASSWORD=your_instagram_password

# Set production settings
heroku config:set LOG_LEVEL=INFO
heroku config:set MAX_FILE_SIZE=52428800
heroku config:set DOWNLOAD_TIMEOUT=300
heroku config:set MAX_RETRIES=3
heroku config:set CLEANUP_INTERVAL=300
heroku config:set HEALTH_CHECK_INTERVAL=30
heroku config:set RATE_LIMIT_PER_USER=10

# Set security
heroku config:set SECRET_KEY=your-secret-key-here
```

### 3. Scale Dynos for Production

```bash
# Scale web dyno
heroku ps:scale web=1

# Scale worker dyno
heroku ps:scale worker=1

# Scale telegram bot dyno
heroku ps:scale telegram=1

# Check dyno status
heroku ps
```

## 🔗 GitHub Auto-Deploy Setup

### 1. Add GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add these secrets:
- `HEROKU_API_KEY`: Your Heroku API key
- `HEROKU_APP_NAME`: Your Heroku app name
- `HEROKU_EMAIL`: Your Heroku email
- `HEROKU_APP_URL`: Your Heroku app URL

### 2. Get Heroku API Key

```bash
# Generate API key
heroku authorizations:create

# Or get existing key
heroku authorizations
```

### 3. Enable GitHub Actions

The `.github/workflows/deploy.yml` file will automatically:
- Run tests on every push
- Deploy to Heroku on main/master branch
- Run health checks after deployment
- Notify deployment status

## 📱 Platform Configuration

### Telegram Bot (@EZMediaFetchBot)

**Bio:**
```
🤖 MediaFetch - Download videos from YouTube, TikTok, Instagram & more!

🎬 Auto-deliver Instagram content to Telegram
📱 Send /bind to start automatic content delivery
🔗 Connect with @mediafetchbot on Instagram

Features:
• Multi-platform video downloads
• Instagram content auto-delivery
• Smart compression & optimization
• 24/7 automated service

Start: /start
Help: /help
Bind Instagram: /bind

#MediaFetch #VideoDownload #Instagram #AutoDelivery
```

**Commands to set in BotFather:**
```
start - Start MediaFetch bot
help - Get help and commands
bind - Generate Instagram binding code
bindings - View your active bindings
unbind - Remove Instagram binding
status - Check download status
cancel - Cancel current download
```

### Instagram Bot (@mediafetchbot)

**Bio (Max 150 chars):**
```
🤖 MediaFetch Bot - Auto-deliver Instagram content to Telegram

📱 Send /bind to @EZMediaFetchBot on Telegram, get code, send here = automatic content delivery!

🎬 Reels, stories, posts → Telegram automatically

🔗 @EZMediaFetchBot #MediaFetch #AutoDelivery
```

## 🚀 Deployment Commands

### Initial Deployment

```bash
# Add Heroku remote
heroku git:remote -a your-app-name

# Push to Heroku
git push heroku main

# Run database migrations
heroku run python -c "from database_schema import *; create_tables()"
```

### Update Deployment

```bash
# Push changes
git push heroku main

# Or force push if needed
git push heroku main --force
```

### Monitor Deployment

```bash
# View logs
heroku logs --tail

# Check app status
heroku ps

# Monitor dynos
heroku ps:scale web=1 worker=1 telegram=1
```

## 📊 Production Monitoring

### Health Check Endpoints

- `/` - Basic health check
- `/health` - Detailed health status
- `/metrics` - Prometheus metrics
- `/status` - System status

### Monitoring Commands

```bash
# Check app health
curl https://your-app.herokuapp.com/health

# View metrics
curl https://your-app.herokuapp.com/metrics

# Check dyno status
heroku ps
```

## 🔒 Security Checklist

- [ ] Environment variables set (no hardcoded secrets)
- [ ] HTTPS enabled (Heroku default)
- [ ] Rate limiting enabled
- [ ] Input validation implemented
- [ ] Error logging configured
- [ ] File upload restrictions set
- [ ] CORS configured properly
- [ ] Security headers set

## 🚨 Troubleshooting

### Common Issues

1. **Build Failures**
   ```bash
   heroku logs --tail
   heroku buildpacks
   ```

2. **Runtime Errors**
   ```bash
   heroku logs --tail
   heroku run python app.py
   ```

3. **Dyno Issues**
   ```bash
   heroku ps:restart
   heroku ps:scale web=1
   ```

4. **Environment Variables**
   ```bash
   heroku config
   heroku config:get TELEGRAM_BOT_TOKEN
   ```

### Support Commands

```bash
# Restart all dynos
heroku restart

# View recent logs
heroku logs --tail -n 100

# Check app info
heroku info

# Open app in browser
heroku open
```

## 📈 Scaling for Production

### Performance Optimization

```bash
# Scale web dynos
heroku ps:scale web=2

# Scale worker dynos
heroku ps:scale worker=2

# Scale telegram bot dynos
heroku ps:scale telegram=2
```

### Monitoring Tools

- **Heroku Metrics**: Built-in performance monitoring
- **Logs**: Real-time log streaming
- **Add-ons**: New Relic, Papertrail, etc.

## 🎯 Production Checklist

- [ ] Heroku app created and configured
- [ ] Environment variables set
- [ ] Buildpacks configured
- [ ] Dynos scaled appropriately
- [ ] GitHub Actions configured
- [ ] Auto-deploy working
- [ ] Health checks passing
- [ ] Monitoring enabled
- [ ] Security measures implemented
- [ ] Backup strategy in place

## 🆘 Support

- **Heroku Support**: https://help.heroku.com/
- **GitHub Actions**: https://docs.github.com/en/actions
- **MediaFetch Issues**: https://github.com/codermillat/MediaFetch/issues

---

**🚀 Your MediaFetch app is now production-ready with auto-deploy!**
