"""
Complete GST Filing Flow Test
This script simulates the entire user journey from GSTIN to SMS link generation.
"""

import requests
import json
from datetime import datetime

# Use Railway production URL
BASE_URL = "https://api-nileasy.up.railway.app/api/v1"

def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_response(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))

def main():
    print("\n🚀 NilEasy - Complete GST Filing Flow Test")
    print("This will walk you through the entire filing process step-by-step.\n")
    
    # ============================================================================
    # STEP 1: Enter GSTIN
    # ============================================================================
    print_section("STEP 1: Enter GSTIN")
    
    gstin = input("Enter GSTIN (or press Enter for test GSTIN 29AABCU9603R1ZX): ").strip()
    if not gstin:
        gstin = "29AABCU9603R1ZX"
    
    print(f"\n✅ Using GSTIN: {gstin}")
    print("\n📡 Validating GSTIN and fetching captcha from GST portal...")
    
    response = requests.post(f"{BASE_URL}/validate-gstin", json={"gstin": gstin})
    result = response.json()
    
    print("\n📥 Response:")
    print_response(result)
    
    if not result.get("valid"):
        print(f"\n❌ Error: {result.get('error')}")
        return
    
    captcha_url = result.get("captcha_url")
    session_id = result.get("session_id")
    
    print(f"\n✅ GSTIN validated successfully!")
    print(f"📷 Captcha URL: {captcha_url}")
    print(f"🔑 Session ID: {session_id}")
    
    # ============================================================================
    # STEP 2: Solve Captcha (Manual Input)
    # ============================================================================
    print_section("STEP 2: Solve Captcha")
    
    print(f"\n📷 Open this URL in your browser to see the captcha:")
    print(f"   {captcha_url}")
    print("\nNOTE: Since we're testing locally, the actual GST captcha might not load.")
    print("      In production, users would see the real captcha image.\n")
    
    captcha_text = input("Enter the captcha text (or press Enter to skip for testing): ").strip()
    
    if captcha_text:
        print(f"\n📡 Verifying captcha and fetching business details...")
        
        response = requests.post(
            f"{BASE_URL}/verify-captcha",
            json={
                "session_id": session_id,
                "gstin": gstin,
                "captcha": captcha_text
            }
        )
        result = response.json()
        
        print("\n📥 Response:")
        print_response(result)
        
        if result.get("success"):
            print("\n✅ Captcha verified successfully!")
            
            details = result.get("business_details", {})
            print("\n📋 Business Details:")
            print(f"   Business Name: {details.get('business_name')}")
            print(f"   Legal Name: {details.get('legal_name')}")
            print(f"   Address: {details.get('address')}")
            print(f"   Registration Date: {details.get('registration_date')}")
            print(f"   Status: {details.get('status')}")
            
            confirm = input("\n✓ Confirm these details? (yes/no): ").strip().lower()
            if confirm not in ['yes', 'y']:
                print("\n❌ Details not confirmed. Exiting.")
                return
        else:
            print(f"\n❌ Captcha verification failed: {result.get('error')}")
            print("\n⚠️  Continuing with test flow anyway...")
    else:
        print("\n⚠️  Skipping captcha verification (test mode)")
    
    # ============================================================================
    # STEP 3: Select GST Type
    # ============================================================================
    print_section("STEP 3: Select GST Return Type")
    
    print("\nAvailable GST Types:")
    print("  1. GSTR-3B (3B) - Monthly summary return")
    print("  2. GSTR-1 (R1) - Outward supplies details")
    print("  3. CMP-08 (C8) - Composition scheme quarterly return")
    
    gst_type_choice = input("\nSelect type (1, 2, or 3, or press Enter for 3B): ").strip()
    
    if gst_type_choice == "2":
        gst_type = "R1"
    elif gst_type_choice == "3":
        gst_type = "C8"
    else:
        gst_type = "3B"
    
    print(f"\n✅ Selected: GSTR-{gst_type if gst_type != 'C8' else 'CMP-08 (C8)'}")
    
    # ============================================================================
    # STEP 4: Enter Period (MMYYYY)
    # ============================================================================
    print_section("STEP 4: Enter Filing Period")
    
    print("\nEnter the filing period in MMYYYY format")
    print("Examples:")
    print("  - 012026 (January 2026)")
    print("  - 022025 (February 2025)")
    
    current_month = datetime.now().strftime("%m%Y")
    period = input(f"\nEnter period (or press Enter for {current_month}): ").strip()
    
    if not period:
        period = current_month
    
    # Validate period format
    if len(period) != 6 or not period.isdigit():
        print(f"\n❌ Invalid period format. Using default: {current_month}")
        period = current_month
    
    month = period[:2]
    year = period[2:]
    
    month_names = {
        "01": "January", "02": "February", "03": "March", "04": "April",
        "05": "May", "06": "June", "07": "July", "08": "August",
        "09": "September", "10": "October", "11": "November", "12": "December"
    }
    
    print(f"\n✅ Selected Period: {month_names.get(month, month)} {year}")
    
    # ============================================================================
    # STEP 5: Generate SMS Link
    # ============================================================================
    print_section("STEP 5: Generate SMS Link")
    
    print(f"\n📡 Generating SMS deep link for filing...")
    print(f"   GSTIN: {gstin}")
    print(f"   Type: GSTR-{gst_type}")
    print(f"   Period: {month_names.get(month, month)} {year}")
    
    response = requests.post(
        f"{BASE_URL}/generate-sms-link",
        json={
            "gstin": gstin,
            "gst_type": gst_type,
            "period": period
        }
    )
    result = response.json()
    
    print("\n📥 Response:")
    print_response(result)
    
    if not result.get("success"):
        print(f"\n❌ Error: {result.get('error')}")
        return
    
    print("\n✅ SMS Link Generated Successfully!")
    print("\n" + "=" * 80)
    print("📱 SMS DETAILS")
    print("=" * 80)
    print(f"\n📝 SMS Preview: {result.get('sms_preview')}")
    print(f"\n🔗 Clickable Link: {result.get('sms_link')}")
    print(f"\n{result.get('instruction')}")
    print(f"\n{result.get('warning')}")
    
    # ============================================================================
    # STEP 6: Track Completion (Optional)
    # ============================================================================
    print_section("STEP 6: Track Filing Completion")
    
    track = input("\nDo you want to track this as completed? (yes/no): ").strip().lower()
    
    if track in ['yes', 'y']:
        phone = input("Enter your phone number (or press Enter for test): ").strip()
        if not phone:
            phone = "+919876543210"
        
        status = input("Enter status (completed/failed, or press Enter for completed): ").strip().lower()
        if status not in ['completed', 'failed']:
            status = 'completed'
        
        print(f"\n📡 Tracking filing as '{status}'...")
        
        response = requests.post(
            f"{BASE_URL}/track-completion",
            json={
                "phone": phone,
                "gstin": gstin,
                "gst_type": gst_type,
                "period": period,
                "status": status
            }
        )
        result = response.json()
        
        print("\n📥 Response:")
        print_response(result)
        
        if result.get("tracked"):
            print(f"\n✅ {result.get('message')}")
    
    # ============================================================================
    # SUMMARY
    # ============================================================================
    print_section("🎉 FLOW COMPLETED SUCCESSFULLY!")
    
    print("\n📊 Summary:")
    print(f"   GSTIN: {gstin}")
    print(f"   Type: GSTR-{gst_type}")
    print(f"   Period: {month_names.get(month, month)} {year}")
    print(f"   SMS Link: Generated ✅")
    
    print("\n" + "=" * 80)
    print("\n✨ You can now use this SMS link to file your GST return!")
    print("   The link will open your SMS app with pre-filled message to 14409.\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
