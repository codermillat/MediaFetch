# MediaFetch Telegram Bot 🎬

A production-ready Telegram bot for downloading media from various platforms including YouTube, TikTok, Instagram, Vimeo, and many more. Built with modern Python practices and optimized for Heroku deployment.

## ✨ Features

- **Multi-Platform Support**: Download from YouTube, TikTok, Instagram, Vimeo, Twitter, Reddit, SoundCloud, and more
- **Instagram Integration**: Fetch posts, stories, and monitor accounts for new content
- **🤖 Automatic Monitoring**: Automatically detect and deliver new Instagram reels/posts to your Telegram
- **Smart Media Processing**: Automatic compression and optimization for Telegram's 50MB limit
- **Production Ready**: Comprehensive error handling, logging, monitoring, and health checks
- **Heroku Optimized**: Built specifically for Heroku deployment with proper dyno management
- **Rate Limiting**: Built-in user rate limiting to prevent abuse
- **Metrics & Monitoring**: Prometheus metrics and comprehensive logging
- **Background Processing**: Worker dyno for file cleanup and media processing
- **Security First**: Environment-based configuration with no hardcoded secrets

## 🚀 Quick Deploy

[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/codermillat/MediaFetch)

## 🏗️ Architecture

The application is designed with a modern, scalable architecture:

- **Web Dyno** (`app.py`): HTTP endpoints, health checks, and metrics
- **Worker Dyno** (`worker.py`): Background tasks, file cleanup, and media processing
- **Modular Design**: Clean separation of concerns with dedicated modules
- **Async Support**: Full async/await support for better performance
- **Error Handling**: Comprehensive error handling and recovery

## 📋 Prerequisites

- Python 3.11+
- Heroku account
- Telegram bot token from [@BotFather](https://t.me/BotFather)
- FFmpeg (automatically installed via Heroku buildpack)

## 🛠️ Installation

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/codermillat/MediaFetch.git
   cd MediaFetch
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your bot token
   ```

4. **Run locally**
   ```bash
   # Start the web application
   python app.py
   
   # Start the worker (in another terminal)
   python worker.py
   ```

### Heroku Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive deployment instructions.

### Instagram Integration

See [INSTAGRAM_SETUP.md](INSTAGRAM_SETUP.md) for detailed Instagram integration setup.

### 🤖 Automatic Instagram Monitoring

See [AUTO_MONITORING.md](AUTO_MONITORING.md) for the complete guide to automatic content delivery.

### 📱 Instagram DM Monitoring

See [INSTAGRAM_DM_MONITORING.md](INSTAGRAM_DM_MONITORING.md) for the complete guide to monitoring DMs and auto-delivering content to senders.

## 🔧 Configuration

All configuration is handled through environment variables:

### Required
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token

### Optional
- `ENVIRONMENT`: Set to "production" for production deployment
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `MAX_FILE_SIZE`: Maximum file size in bytes (default: 50MB)
- `DOWNLOAD_TIMEOUT`: Download timeout in seconds (default: 300)
- `MAX_RETRIES`: Maximum download retries (default: 3)
- `CLEANUP_INTERVAL`: File cleanup interval in seconds (default: 300)
- `HEALTH_CHECK_INTERVAL`: Health check interval in seconds (default: 30)
- `RATE_LIMIT_PER_USER`: Downloads per user per hour (default: 10)

## 📱 Usage

1. **Start the bot**: Send `/start` to get started
2. **Download media**: Send any supported media link
3. **Check status**: Use `/status` to see your download progress
4. **Get help**: Use `/help` for available commands
5. **Cancel downloads**: Use `/cancel` to cancel current download

### Supported Platforms

- **Video Platforms**: YouTube, TikTok, Instagram, Vimeo, Twitter, Facebook, Reddit
- **Audio Platforms**: SoundCloud, Spotify, Apple Music
- **Image Platforms**: Instagram, Twitter, Reddit

## 📊 Monitoring & Health Checks

### Health Check Endpoints

- `/` - Basic health check
- `/metrics` - Prometheus metrics
- `/start-bot` - Start the Telegram bot
- `/stop-bot` - Stop the Telegram bot

### Metrics Available

- Download counts and success rates
- User activity and engagement
- System resource usage
- Error rates and types
- Platform-specific download statistics

## 🔒 Security Features

- **Environment Variables**: All sensitive data stored in environment variables
- **Rate Limiting**: Built-in user rate limiting to prevent abuse
- **Input Validation**: Comprehensive URL and input validation
- **File Sanitization**: Safe filename handling and file operations
- **Error Logging**: Detailed error logging without exposing sensitive information

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest

# Run with coverage
pytest --cov=telegram_media_bot
```

## 📁 Project Structure

```
MediaFetch/
├── app.py                          # Main web application
├── worker.py                       # Background worker process
├── telegram_media_bot/            # Core bot package
│   ├── __init__.py               # Package initialization
│   ├── bot.py                    # Main bot implementation
│   ├── config.py                 # Configuration management
│   ├── media_downloader.py       # Media download handling
│   ├── media_processor.py        # Media processing and optimization
│   ├── metrics.py                # Metrics collection
│   ├── utils.py                  # Utility functions
│   └── worker.py                 # Background worker
├── requirements.txt               # Python dependencies
├── Procfile                      # Heroku process definitions
├── runtime.txt                   # Python version specification
├── app.json                      # Heroku app configuration
├── env.example                   # Environment variables template
├── .gitignore                    # Git ignore rules
├── DEPLOYMENT.md                 # Deployment guide
└── README.md                     # This file
```

## 🚨 Important Notes

- **File Size Limits**: Heroku has a 50MB file size limit for Telegram
- **Ephemeral Filesystem**: Files are automatically cleaned up after processing
- **Rate Limits**: Users are limited to 10 downloads per hour by default
- **Memory Usage**: Monitor memory usage and scale dynos as needed

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

If you need help:

1. Check the [deployment guide](DEPLOYMENT.md)
2. Review the logs: `heroku logs --tail`
3. Open an issue on GitHub
4. Check Heroku status: [status.heroku.com](https://status.heroku.com)

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Excellent Telegram bot library
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Powerful media downloader
- [FFmpeg](https://ffmpeg.org/) - Media processing capabilities
- [Heroku](https://heroku.com) - Platform for deployment

---

**Made with ❤️ for the Telegram community**
