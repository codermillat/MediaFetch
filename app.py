#!/usr/bin/env python3
"""
MediaFetch Telegram Bot - Main Application
Heroku-compatible web application with health checks and metrics
"""

import os
import logging
from flask import Flask, jsonify
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
from telegram_media_bot.bot import MediaFetchBot
from telegram_media_bot.metrics import MetricsCollector

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize global metrics instance
global_metrics = MetricsCollector()
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
    try:
        # Update system metrics before returning
        global_metrics.update_system_metrics()
        metrics_data = global_metrics.get_prometheus_metrics()

        # Ensure we return bytes for prometheus format
        if isinstance(metrics_data, str):
            metrics_data = metrics_data.encode('utf-8')

        return metrics_data, 200, {'Content-Type': CONTENT_TYPE_LATEST}

    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        # Return a minimal metrics response on error
        error_response = b"# Error generating metrics\n"
        return error_response, 500, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/start-bot')
def start_bot():
    """Start the Telegram bot"""
    global bot
    try:
        if bot is None:
            # Initialize bot with global metrics instance
            from telegram_media_bot.bot import MediaFetchBot
            bot = MediaFetchBot(metrics_instance=global_metrics)
            return jsonify({'status': 'Bot initialized', 'message': 'Bot created with shared metrics'})
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

@app.route('/test-binding')
def test_binding():
    """Test the binding system functionality"""
    try:
        from binding_manager import BindingManager
        bm = BindingManager(None)
        return jsonify({
            'status': 'success',
            'binding_system': 'ready',
            'code_length': bm.binding_code_length,
            'expiry_hours': bm.binding_code_expiry_hours,
            'max_attempts': bm.max_binding_attempts
        })
    except Exception as e:
        logger.error(f"Binding system test failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/test-instagram')
def test_instagram():
    """Test the Instagram integration"""
    try:
        from instagram_bot_integration import InstagramBotIntegration
        return jsonify({
            'status': 'success',
            'instagram_integration': 'ready',
            'message': 'Instagram bot integration loaded successfully'
        })
    except Exception as e:
        logger.error(f"Instagram integration test failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)

# Production configuration
app.config['ENV'] = os.environ.get('FLASK_ENV', 'production')
app.config['DEBUG'] = False
app.config['TESTING'] = False
