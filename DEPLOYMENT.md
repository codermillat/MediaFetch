# MediaFetch Telegram Bot - Heroku Deployment Guide

This guide will walk you through deploying the MediaFetch Telegram bot to Heroku.

## Prerequisites

1. **Heroku Account**: Sign up at [heroku.com](https://heroku.com)
2. **Heroku CLI**: Install from [devcenter.heroku.com/articles/heroku-cli](https://devcenter.heroku.com/articles/heroku-cli)
3. **Git**: Ensure your project is in a Git repository
4. **Telegram Bot Token**: Get from [@BotFather](https://t.me/BotFather) on Telegram

## Quick Deploy (One-Click)

[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/codermillat/MediaFetch)

## Manual Deployment

### Step 1: Prepare Your Bot Token

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Create a new bot with `/newbot`
3. Copy the bot token (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Deploy to Heroku

```bash
# Login to Heroku
heroku login

# Create a new Heroku app
heroku create your-mediafetch-bot

# Set the bot token
heroku config:set TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN_HERE"

# Set environment variables
heroku config:set ENVIRONMENT=production
heroku config:set LOG_LEVEL=INFO
heroku config:set MAX_FILE_SIZE=52428800
heroku config:set DOWNLOAD_TIMEOUT=300
heroku config:set MAX_RETRIES=3
heroku config:set CLEANUP_INTERVAL=300
heroku config:set HEALTH_CHECK_INTERVAL=30
heroku config:set RATE_LIMIT_PER_USER=10

# Add Redis addon (for rate limiting and caching)
heroku addons:create heroku-redis:mini

# Add FFmpeg buildpack
heroku buildpacks:add https://github.com/heroku/heroku-buildpack-ffmpeg-latest

# Deploy the application
git push heroku main

# Scale the dynos
heroku ps:scale web=1 worker=1

# Open the application
heroku open
```

### Step 3: Verify Deployment

1. Check the web dyno: `heroku logs --tail --dyno web`
2. Check the worker dyno: `heroku logs --tail --dyno worker`
3. Visit your app URL to see the health check endpoint

## Configuration Options

### Required Environment Variables

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token

### Optional Environment Variables

- `ENVIRONMENT`: Set to "production" for production deployment
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `MAX_FILE_SIZE`: Maximum file size in bytes (default: 50MB)
- `DOWNLOAD_TIMEOUT`: Download timeout in seconds (default: 300)
- `MAX_RETRIES`: Maximum download retries (default: 3)
- `CLEANUP_INTERVAL`: File cleanup interval in seconds (default: 300)
- `HEALTH_CHECK_INTERVAL`: Health check interval in seconds (default: 30)
- `RATE_LIMIT_PER_USER`: Downloads per user per hour (default: 10)

## Architecture

The application runs on two dynos:

1. **Web Dyno** (`app.py`): Handles HTTP requests, health checks, and metrics
2. **Worker Dyno** (`worker.py`): Handles background tasks, file cleanup, and media processing

## Monitoring

### Health Check Endpoints

- `/` - Basic health check
- `/metrics` - Prometheus metrics
- `/start-bot` - Start the Telegram bot
- `/stop-bot` - Stop the Telegram bot

### Logs

```bash
# View all logs
heroku logs --tail

# View specific dyno logs
heroku logs --tail --dyno web
heroku logs --tail --dyno worker

# View recent logs
heroku logs --num 100
```

### Metrics

The application exposes Prometheus metrics at `/metrics` for monitoring:
- Download counts and success rates
- User activity
- System resource usage
- Error rates

## Troubleshooting

### Common Issues

1. **Bot not responding**: Check if the worker dyno is running
2. **Downloads failing**: Check file size limits and timeout settings
3. **Memory issues**: Scale up to a larger dyno size
4. **FFmpeg errors**: Ensure the FFmpeg buildpack is added

### Debug Commands

```bash
# Check dyno status
heroku ps

# Check environment variables
heroku config

# Restart the application
heroku restart

# Scale dynos
heroku ps:scale web=1 worker=1

# Check buildpacks
heroku buildpacks
```

### Performance Tuning

1. **Increase dyno size** for better performance:
   ```bash
   heroku ps:type web=standard-1x
   heroku ps:type worker=standard-1x
   ```

2. **Add more worker dynos** for parallel processing:
   ```bash
   heroku ps:scale worker=2
   ```

3. **Optimize cleanup intervals** based on usage:
   ```bash
   heroku config:set CLEANUP_INTERVAL=600  # 10 minutes
   ```

## Security Considerations

1. **Never commit your bot token** to version control
2. **Use environment variables** for all sensitive configuration
3. **Enable rate limiting** to prevent abuse
4. **Monitor logs** for suspicious activity
5. **Regular updates** of dependencies

## Maintenance

### Regular Tasks

1. **Monitor logs** for errors and performance issues
2. **Check metrics** for usage patterns
3. **Update dependencies** regularly
4. **Clean up old logs** and temporary files
5. **Monitor Heroku addon usage** and costs

### Updates

```bash
# Pull latest changes
git pull origin main

# Deploy updates
git push heroku main

# Restart if needed
heroku restart
```

## Support

If you encounter issues:

1. Check the logs: `heroku logs --tail`
2. Review this deployment guide
3. Check Heroku status: [status.heroku.com](https://status.heroku.com)
4. Open an issue on GitHub

## Cost Optimization

- **Free tier**: No longer available on Heroku
- **Basic dynos**: $7/month per dyno
- **Redis addon**: $15/month
- **Total**: ~$29/month for basic setup

Consider alternatives like:
- Railway.app
- Render.com
- DigitalOcean App Platform
- AWS Lambda + API Gateway
