"""
Test script to verify Twilio webhook is working correctly
"""
import httpx
import asyncio

async def test_webhook():
    """Simulate what Twilio sends to our webhook"""
    
    url = "http://localhost:8000/api/v1/webhook"
    
    # This is what Twilio sends (form data, not JSON!)
    data = {
        "From": "whatsapp:+919876543210",  # Replace with your number
        "Body": "Hi",
        "ProfileName": "Test User",
        "MessageSid": "SM1234567890"
    }
    
    print(f"🧪 Testing webhook: {url}")
    print(f"📤 Sending data: {data}\n")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                data=data,  # Form data, not json!
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0
            )
            
            print(f"✅ Status: {response.status_code}")
            print(f"📥 Response: {response.text[:200]}")
            
            if response.status_code == 200:
                print("\n✅ Webhook is working!")
            else:
                print(f"\n❌ Webhook returned {response.status_code}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_webhook())
