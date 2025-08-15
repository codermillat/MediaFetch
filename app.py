#!/usr/bin/env python3
"""
MediaFetch Telegram Bot - Main Application
Heroku-compatible web application with health checks and metrics
"""

import os
import logging
from flask import Flask, jsonify
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from telegram_media_bot.bot import MediaFetchBot

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize bot instance
bot = None

@app.route('/')
def health_check():
    """Health check endpoint for Heroku"""
    return jsonify({
        'status': 'healthy',
        'service': 'MediaFetch Telegram Bot',
        'version': '1.0.0'
    })

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/start-bot')
def start_bot():
    """Start the Telegram bot"""
    global bot
    try:
        if bot is None:
            bot = MediaFetchBot()
            bot.start()
            return jsonify({'status': 'Bot started successfully'})
        else:
            return jsonify({'status': 'Bot already running'})
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/stop-bot')
def stop_bot():
    """Stop the Telegram bot"""
    global bot
    try:
        if bot:
            bot.stop()
            bot = None
            return jsonify({'status': 'Bot stopped successfully'})
        else:
            return jsonify({'status': 'No bot running'})
    except Exception as e:
        logger.error(f"Failed to stop bot: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
