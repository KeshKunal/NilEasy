"""
Test Twilio WhatsApp Integration

Run this script to verify Twilio is configured correctly
and can send messages.

Usage: python scripts/test_twilio.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.twilio_service import twilio_service
from app.core.config import settings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_twilio_config():
    """Test if Twilio is properly configured"""
    print("=" * 60)
    print("  Twilio Configuration Test")
    print("=" * 60 + "\n")
    
    print(f"Account SID: {settings.TWILIO_ACCOUNT_SID[:10]}..." if settings.TWILIO_ACCOUNT_SID else "❌ Not set")
    print(f"Auth Token: {'✅ Set' if settings.TWILIO_AUTH_TOKEN else '❌ Not set'}")
    print(f"WhatsApp Number: {settings.TWILIO_WHATSAPP_NUMBER}")
    print(f"\nConfiguration valid: {'✅ Yes' if twilio_service.is_configured() else '❌ No'}\n")
    
    if not twilio_service.is_configured():
        print("⚠️  Please update TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env file")
        return False
    
    return True


async def test_send_message():
    """Test sending a WhatsApp message"""
    print("=" * 60)
    print("  Test Message Sending")
    print("=" * 60 + "\n")
    
    # Ask for phone number
    phone = input("Enter your WhatsApp number (with country code, e.g., +919876543210): ")
    
    if not phone.startswith("+"):
        print("❌ Phone number must start with + and country code")
        return
    
    print(f"\n📤 Sending test message to {phone}...")
    
    result = await twilio_service.send_message(
        to_phone=phone,
        message="🧪 *Test Message from NilEasy*\n\nIf you received this, Twilio integration is working! ✅\n\nReply 'Hi' to start the filing process."
    )
    
    if result["success"]:
        print(f"\n✅ Message sent successfully!")
        print(f"Message SID: {result.get('message_sid')}")
        print(f"Status: {result.get('status')}")
        print("\n📱 Check your WhatsApp!")
    else:
        print(f"\n❌ Failed to send message")
        print(f"Error: {result.get('error')}")


async def test_webhook_endpoint():
    """Check if webhook endpoint is accessible"""
    print("\n" + "=" * 60)
    print("  Webhook Configuration")
    print("=" * 60 + "\n")
    
    app_url = settings.APP_URL
    webhook_url = f"{app_url}/api/v1/webhook"
    
    print(f"Webhook URL: {webhook_url}")
    print(f"\n⚠️  Make sure to configure this URL in Twilio Console:")
    print(f"   Messaging → Try it out → Sandbox Configuration")
    print(f"   Set 'When a message comes in' to: {webhook_url}\n")


async def main():
    """Run all tests"""
    print("\n🧪 NilEasy Twilio Integration Test\n")
    
    # Test 1: Configuration
    config_ok = await test_twilio_config()
    
    if not config_ok:
        print("\n❌ Configuration test failed. Please fix .env file and try again.")
        return
    
    # Test 2: Webhook info
    await test_webhook_endpoint()
    
    # Test 3: Send message (optional)
    print("=" * 60)
    test_send = input("\nDo you want to send a test message? (y/n): ")
    
    if test_send.lower() == 'y':
        await test_send_message()
    else:
        print("\n✅ Configuration test passed!")
        print("When ready, send a test message from WhatsApp to verify end-to-end.")
    
    print("\n" + "=" * 60)
    print("\n✅ All tests completed!")
    print("\nNext steps:")
    print("1. Start ngrok: ngrok http 8000")
    print("2. Update APP_URL in .env with ngrok HTTPS URL")
    print("3. Configure Twilio webhook with ngrok URL")
    print("4. Start server: uvicorn app.main:app --reload")
    print("5. Send 'Hi' from WhatsApp to test!")
    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
