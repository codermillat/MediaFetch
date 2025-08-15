#!/usr/bin/env python3
"""
MediaFetch Worker Process
Handles background tasks and media downloads for Heroku
"""

import os
import logging
import asyncio
from telegram_media_bot.worker import MediaWorker

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    """Main worker function"""
    try:
        worker = MediaWorker()
        await worker.start()
        
        # Keep the worker running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker error: {e}")
        raise

if __name__ == '__main__':
    asyncio.run(main())
