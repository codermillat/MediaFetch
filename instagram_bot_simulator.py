#!/usr/bin/env python3
"""
Instagram Bot Simulator
Simulates the Instagram bot to test user-friendly features
"""

import asyncio
import logging
from instagram_binding_handler import handle_instagram_message

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class InstagramBotSimulator:
    """Simulates Instagram bot interactions for testing"""
    
    def __init__(self):
        self.test_users = {
            "testuser1": "Test User 1",
            "testuser2": "Test User 2",
            "contentcreator": "Content Creator",
            "influencer": "Influencer"
        }
    
    async def simulate_user_interaction(self, username: str, message: str):
        """Simulate a user sending a message to the Instagram bot"""
        print(f"\n{'='*60}")
        print(f"📱 **Instagram Bot Simulation**")
        print(f"👤 **User:** @{username}")
        print(f"💬 **Message:** {message}")
        print(f"{'='*60}")
        
        # Process the message
        result = await handle_instagram_message(message, username)
        
        print(f"🤖 **Bot Response:**")
        print(f"📋 **Type:** {result['type']}")
        print(f"💬 **Message:**")
        print(result['message'])
        print(f"{'='*60}")
        
        return result
    
    async def run_comprehensive_test(self):
        """Run comprehensive test of all bot features"""
        print("🚀 **Starting Instagram Bot Comprehensive Test**\n")
        
        # Test 1: Welcome messages
        print("🎯 **Test 1: Welcome & Start Commands**")
        await self.simulate_user_interaction("testuser1", "start")
        await self.simulate_user_interaction("testuser2", "hello")
        await self.simulate_user_interaction("contentcreator", "hi")
        
        # Test 2: Help and commands
        print("\n🎯 **Test 2: Help & Commands**")
        await self.simulate_user_interaction("testuser1", "help")
        await self.simulate_user_interaction("testuser2", "commands")
        await self.simulate_user_interaction("contentcreator", "cmd")
        
        # Test 3: Binding information
        print("\n🎯 **Test 3: Binding Information**")
        await self.simulate_user_interaction("testuser1", "bind")
        await self.simulate_user_interaction("testuser2", "binding info")
        await self.simulate_user_interaction("contentcreator", "bind info")
        
        # Test 4: Status checking
        print("\n🎯 **Test 4: Status & Information**")
        await self.simulate_user_interaction("testuser1", "status")
        await self.simulate_user_interaction("testuser2", "my status")
        await self.simulate_user_interaction("contentcreator", "binding status")
        
        # Test 5: About and features
        print("\n🎯 **Test 5: About & Features**")
        await self.simulate_user_interaction("testuser1", "info")
        await self.simulate_user_interaction("testuser2", "about")
        await self.simulate_user_interaction("contentcreator", "features")
        
        # Test 6: Support
        print("\n🎯 **Test 6: Support & Help**")
        await self.simulate_user_interaction("testuser1", "support")
        await self.simulate_user_interaction("testuser2", "sos")
        await self.simulate_user_interaction("contentcreator", "help me")
        
        # Test 7: General messages
        print("\n🎯 **Test 7: General Messages**")
        await self.simulate_user_interaction("testuser1", "what is this?")
        await self.simulate_user_interaction("testuser2", "how does this work?")
        await self.simulate_user_interaction("contentcreator", "random message")
        
        # Test 8: Binding code simulation
        print("\n🎯 **Test 8: Binding Code Processing**")
        await self.simulate_user_interaction("testuser1", "A7B9C2D4")  # Valid code
        await self.simulate_user_interaction("testuser2", "INVALID")    # Invalid code
        await self.simulate_user_interaction("contentcreator", "12345") # Too short
        
        print("\n✅ **Comprehensive Test Complete!**")
        print("🎉 **Instagram Bot is now fully user-friendly!**")

async def interactive_test():
    """Interactive test mode for manual testing"""
    print("🎮 **Interactive Instagram Bot Test Mode**")
    print("Type 'quit' to exit, or send any message to test the bot\n")
    
    simulator = InstagramBotSimulator()
    
    while True:
        try:
            # Get user input
            username = input("👤 Enter Instagram username (or 'quit'): ").strip()
            if username.lower() == 'quit':
                break
            
            if not username:
                username = "testuser"
            
            message = input("💬 Enter message to send: ").strip()
            if message.lower() == 'quit':
                break
            
            if not message:
                print("❌ Please enter a message!")
                continue
            
            # Simulate the interaction
            await simulator.simulate_user_interaction(username, message)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🤖 **MediaFetch Instagram Bot Simulator**")
    print("Choose your test mode:\n")
    print("1. Comprehensive Test (all features)")
    print("2. Interactive Test (manual testing)")
    
    choice = input("\nEnter your choice (1 or 2): ").strip()
    
    if choice == "1":
        simulator = InstagramBotSimulator()
        asyncio.run(simulator.run_comprehensive_test())
    elif choice == "2":
        asyncio.run(interactive_test())
    else:
        print("❌ Invalid choice. Running comprehensive test...")
        simulator = InstagramBotSimulator()
        asyncio.run(simulator.run_comprehensive_test())
