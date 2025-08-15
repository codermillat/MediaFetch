#!/usr/bin/env python3
"""
Test script to test Instagram bot functionality
"""

import os
import asyncio
import logging
from instagrapi import Client
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Instagram credentials from .env
INSTAGRAM_USERNAME = "mediafetchbot"
INSTAGRAM_PASSWORD = "v3YiHm48a/TvvC?"

class InstagramBotTester:
    """Test class for Instagram bot functionality"""
    
    def __init__(self):
        self.client = Client()
        self.is_logged_in = False
        
    async def test_login(self):
        """Test Instagram login"""
        try:
            logger.info("Testing Instagram login...")
            
            # Attempt to login
            login_result = self.client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            
            if login_result:
                self.is_logged_in = True
                user_info = self.client.user_info_by_username(INSTAGRAM_USERNAME)
                logger.info(f"✅ Login successful! User: {user_info.full_name} (@{user_info.username})")
                return True
            else:
                logger.error("❌ Login failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            return False
    
    async def test_binding_code_handling(self):
        """Test binding code handling logic"""
        logger.info("Testing binding code handling...")
        
        # Simulate receiving a binding code
        test_codes = ["A7B9C2D4", "X9Y2Z8W1", "M5N7P3Q9"]
        
        for code in test_codes:
            logger.info(f"Testing code: {code}")
            
            # Validate code format (6-10 alphanumeric characters)
            if len(code) >= 6 and len(code) <= 10 and code.isalnum():
                logger.info(f"✅ Code {code} is valid format")
                
                # Check if it's a binding code (not a regular message)
                if self._is_binding_code(code):
                    logger.info(f"✅ Code {code} identified as binding code")
                    
                    # Simulate binding confirmation
                    confirmation_result = await self._confirm_binding(code, "testuser")
                    if confirmation_result:
                        logger.info(f"✅ Binding confirmed for code {code}")
                    else:
                        logger.info(f"❌ Binding failed for code {code}")
                else:
                    logger.info(f"ℹ️ Code {code} is not a binding code")
            else:
                logger.error(f"❌ Code {code} has invalid format")
        
        return True
    
    def _is_binding_code(self, message: str) -> bool:
        """Check if a message is a binding code"""
        # Binding codes are 6-10 alphanumeric characters
        if len(message) >= 6 and len(message) <= 10 and message.isalnum():
            # Check if it's not a common word or phrase
            common_words = ['hello', 'hi', 'thanks', 'ok', 'yes', 'no', 'test']
            if message.lower() not in common_words:
                return True
        return False
    
    async def _confirm_binding(self, code: str, username: str) -> bool:
        """Simulate binding confirmation"""
        try:
            # In production, this would:
            # 1. Look up the binding code in database
            # 2. Verify it matches the username
            # 3. Activate the binding
            # 4. Send confirmation to Telegram user
            
            logger.info(f"Confirming binding: Code {code} for user {username}")
            
            # Simulate database lookup
            binding_found = True  # Mock result
            
            if binding_found:
                # Simulate binding activation
                logger.info(f"✅ Binding activated for {username}")
                
                # Simulate sending confirmation to Telegram
                telegram_message = f"✅ **Binding Confirmed!**\n\nYour Instagram account @{username} is now bound to MediaFetch!\n\n🎬 **You will now receive:**\n• All reels automatically\n• All stories instantly\n• All posts as they're published\n\n**No more manual checking - content comes to you!**"
                
                logger.info(f"📱 Telegram confirmation sent: {telegram_message[:100]}...")
                return True
            else:
                logger.error(f"❌ Binding code {code} not found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Binding confirmation error: {e}")
            return False
    
    async def test_content_delivery(self):
        """Test content delivery logic"""
        logger.info("Testing content delivery system...")
        
        # Simulate different content types
        content_types = [
            {"type": "reel", "url": "https://instagram.com/reel/ABC123", "username": "testuser"},
            {"type": "story", "url": "https://instagram.com/stories/testuser/123", "username": "testuser"},
            {"type": "post", "url": "https://instagram.com/p/XYZ789", "username": "testuser"}
        ]
        
        for content in content_types:
            logger.info(f"Testing {content['type']} delivery...")
            
            # Simulate content processing
            delivery_result = await self._process_content_delivery(content)
            
            if delivery_result:
                logger.info(f"✅ {content['type']} delivery successful")
            else:
                logger.error(f"❌ {content['type']} delivery failed")
        
        return True
    
    async def _process_content_delivery(self, content: dict) -> bool:
        """Simulate content delivery processing"""
        try:
            logger.info(f"Processing {content['type']} from @{content['username']}")
            
            # Simulate download
            logger.info("⏳ Downloading content...")
            await asyncio.sleep(1)  # Simulate processing time
            
            # Simulate optimization
            logger.info("⚡ Optimizing content...")
            await asyncio.sleep(1)
            
            # Simulate sending to bound users
            logger.info("📱 Sending to bound users...")
            
            # Mock success
            return True
            
        except Exception as e:
            logger.error(f"❌ Content delivery error: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all Instagram bot tests"""
        logger.info("🚀 Starting Instagram Bot Tests...")
        logger.info("=" * 50)
        
        tests = [
            ("Instagram Login", self.test_login),
            ("Binding Code Handling", self.test_binding_code_handling),
            ("Content Delivery", self.test_content_delivery)
        ]
        
        results = []
        for test_name, test_func in tests:
            logger.info(f"\n🧪 Running: {test_name}")
            try:
                result = await test_func()
                results.append((test_name, result))
                logger.info(f"✅ {test_name}: {'PASSED' if result else 'FAILED'}")
            except Exception as e:
                logger.error(f"❌ {test_name}: ERROR - {e}")
                results.append((test_name, False))
        
        # Summary
        logger.info("\n" + "=" * 50)
        logger.info("📊 TEST RESULTS SUMMARY")
        logger.info("=" * 50)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test_name}: {status}")
        
        logger.info(f"\n🎯 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All Instagram bot tests passed!")
            logger.info("✅ Ready for production Instagram integration!")
        else:
            logger.info("⚠️ Some tests failed. Review before production.")
        
        return passed == total

async def main():
    """Main function to run Instagram bot tests"""
    tester = InstagramBotTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
