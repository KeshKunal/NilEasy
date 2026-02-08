# NilEasy API Documentation

**Version:** 1.0.0  
**Base URL:** `http://localhost:8001` (Development) | `https://api-nileasy.up.railway.app` (Production)  
**API Prefix:** `/api/v1`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Rate Limiting](#rate-limiting)
4. [Error Handling](#error-handling)
5. [Endpoints](#endpoints)
   - [Validate GSTIN](#1-validate-gstin)
   - [Verify Captcha](#2-verify-captcha)
   - [Generate SMS Link](#3-generate-sms-link)
   - [Track Completion](#4-track-completion)
   - [Health Check](#5-health-check)
6. [Complete Flow Example](#complete-flow-example)
7. [Testing](#testing)

---

## Overview

NilEasy provides a **stateless REST API** for GST Nil Filing automation via WhatsApp. The API is designed for integration with **AiSensy Flow Builder** and follows a 4-step workflow:

```
1. Validate GSTIN → 2. Verify Captcha → 3. Generate SMS Link → 4. Track Completion
```

### Key Features

- ✅ **Stateless Architecture** - No server-side session management
- ✅ **Direct GST Portal Integration** - Real-time captcha and business details
- ✅ **Smart GSTIN Cache** - Returns cached details instantly if GSTIN already verified (no captcha!)
- ✅ **Rate Limited** - 3 captcha attempts per GSTIN per hour
- ✅ **Production Ready** - Comprehensive error handling and logging
- ✅ **Pydantic Validation** - Automatic request/response validation
- ✅ **Multiple Filing Types** - Supports GSTR-3B, GSTR-1, and CMP-08

---

## Authentication

Currently, the API does **not require authentication** for development/testing.

For production deployment, consider implementing:

- API Key authentication via headers
- IP whitelisting for AiSensy servers
- JWT tokens for user sessions

---

## Rate Limiting

### Captcha Rate Limit

- **Limit:** 3 attempts per GSTIN per hour
- **Window:** 3600 seconds (1 hour)
- **Storage:** In-memory (upgrade to Redis for production)

**Response when rate limit exceeded:**

```json
{
  "valid": false,
  "error": "Too many attempts. Please try again in XX minutes.",
  "captcha_url": null,
  "session_id": null
}
```

---

## Error Handling

All endpoints return **HTTP 200** with error details in response body for easier AiSensy integration.

### Standard Error Response Format

```json
{
  "success": false,
  "error": "Human-readable error message",
  ...other fields set to null
}
```

### Common Error Messages

| Error Message                                              | Cause                             | Solution                   |
| ---------------------------------------------------------- | --------------------------------- | -------------------------- |
| `Invalid GSTIN format`                                     | GSTIN doesn't match regex pattern | Check 15-character format  |
| `Too many attempts. Please try again in XX minutes.`       | Rate limit exceeded               | Wait for rate limit window |
| `No active captcha session. Please request a new captcha.` | Session expired/invalid           | Start from Step 1          |
| `Incorrect captcha. Please try again.`                     | Wrong captcha text                | Request new captcha        |
| `GSTIN not found in GST records`                           | Invalid GSTIN                     | Verify GSTIN with business |
| `Failed to fetch captcha from GST portal`                  | GST portal unavailable            | Retry after some time      |

---

## Endpoints

---

### 1. Validate GSTIN

Validates GSTIN format and fetches captcha image from GST portal.

**📌 Smart Caching:** If the GSTIN has been verified before, this endpoint returns cached business details immediately, **skipping the captcha flow entirely**.

**Endpoint:** `POST /api/v1/validate-gstin`

#### Request Body

```json
{
  "gstin": "29AABCU9603R1ZX"
}
```

| Field   | Type   | Required | Description        | Validation                                                         |
| ------- | ------ | -------- | ------------------ | ------------------------------------------------------------------ |
| `gstin` | string | ✅ Yes   | 15-character GSTIN | Regex: `^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$` |

#### Response - Success (New GSTIN)

```json
{
  "valid": true,
  "captcha_url": "http://localhost:8001/api/v1/captcha/29AABCU9603R1ZX",
  "session_id": "8d006cb7-415b-43ea-ad36-01d9e83ba034",
  "business_details": null,
  "error": null
}
```

#### Response - Success (Cached GSTIN - No Captcha Needed)

```json
{
  "valid": true,
  "captcha_url": null,
  "session_id": "cached",
  "business_details": {
    "business_name": "ETERNAL LIMITED",
    "legal_name": "ETERNAL LIMITED",
    "address": "12 R.G. Chambers, 80 ft road, 5th Block, Koramangala, Bengaluru Urban, Karnataka, 560095",
    "registration_date": "01/07/2017",
    "status": "Active",
    "gstin": "29AABCU9603R1ZX"
  },
  "error": null
}
```

**Note:** When `session_id` is `"cached"` and `business_details` is present, skip directly to Step 3 (Generate SMS Link).

| Field              | Type           | Description                                            |
| ------------------ | -------------- | ------------------------------------------------------ |
| `valid`            | boolean        | Whether GSTIN is valid                                 |
| `captcha_url`      | string         | URL to fetch captcha image (PNG) - null if cached      |
| `session_id`       | string         | UUID for captcha verification - "cached" if from cache |
| `business_details` | object \| null | Business details if GSTIN is cached                    |
| `error`            | string \| null | Error message if failed                                |

#### Response - Error

```json
{
  "valid": false,
  "captcha_url": null,
  "session_id": null,
  "error": "Too many attempts. Please try again in 45 minutes."
}
```

#### cURL Example

```bash
curl -X POST http://localhost:8001/api/v1/validate-gstin \
  -H "Content-Type: application/json" \
  -d '{"gstin": "29AABCU9603R1ZX"}'
```

#### Python Example

```python
import requests

response = requests.post(
    "http://localhost:8001/api/v1/validate-gstin",
    json={"gstin": "29AABCU9603R1ZX"}
)
result = response.json()

if result["valid"]:
    print(f"Captcha URL: {result['captcha_url']}")
    print(f"Session ID: {result['session_id']}")
else:
    print(f"Error: {result['error']}")
```

---

### 2. Verify Captcha

Verifies captcha and fetches business details from GST portal.

**Endpoint:** `POST /api/v1/verify-captcha`

#### Request Body

```json
{
  "session_id": "8d006cb7-415b-43ea-ad36-01d9e83ba034",
  "gstin": "29AABCU9603R1ZX",
  "captcha": "ABC123"
}
```

| Field        | Type   | Required | Description             | Validation     |
| ------------ | ------ | -------- | ----------------------- | -------------- |
| `session_id` | string | ✅ Yes   | Session ID from Step 1  | UUID format    |
| `gstin`      | string | ✅ Yes   | 15-character GSTIN      | Same as Step 1 |
| `captcha`    | string | ✅ Yes   | Captcha text from image | Min 3 chars    |

#### Response - Success

```json
{
  "success": true,
  "business_details": {
    "business_name": "ETERNAL LIMITED",
    "legal_name": "ETERNAL LIMITED",
    "address": "12 R.G. Chambers, 80 ft road, 5th Block, Koramangala, Bengaluru Urban, Karnataka, 560095",
    "registration_date": "01/07/2017",
    "status": "Active",
    "gstin": "29AABCU9603R1ZX"
  },
  "error": null
}
```

| Field                                | Type           | Description                          |
| ------------------------------------ | -------------- | ------------------------------------ |
| `success`                            | boolean        | Whether verification succeeded       |
| `business_details`                   | object         | Business information from GST portal |
| `business_details.business_name`     | string         | Trade/Business name                  |
| `business_details.legal_name`        | string         | Legal registered name                |
| `business_details.address`           | string         | Principal place of business address  |
| `business_details.registration_date` | string         | GST registration date (DD/MM/YYYY)   |
| `business_details.status`            | string         | Active/Inactive status               |
| `business_details.gstin`             | string         | Verified GSTIN                       |
| `error`                              | string \| null | Error message if failed              |

#### Response - Error

```json
{
  "success": false,
  "business_details": null,
  "error": "Incorrect captcha. Please try again."
}
```

#### cURL Example

```bash
curl -X POST http://localhost:8001/api/v1/verify-captcha \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "8d006cb7-415b-43ea-ad36-01d9e83ba034",
    "gstin": "29AABCU9603R1ZX",
    "captcha": "ABC123"
  }'
```

#### Python Example

```python
import requests

response = requests.post(
    "http://localhost:8001/api/v1/verify-captcha",
    json={
        "session_id": "8d006cb7-415b-43ea-ad36-01d9e83ba034",
        "gstin": "29AABCU9603R1ZX",
        "captcha": "ABC123"
    }
)
result = response.json()

if result["success"]:
    details = result["business_details"]
    print(f"Business: {details['business_name']}")
    print(f"Legal Name: {details['legal_name']}")
    print(f"Address: {details['address']}")
    print(f"Status: {details['status']}")
else:
    print(f"Error: {result['error']}")
```

---

### 3. Generate SMS Link

Generates SMS deep link for GST Nil filing to 14409.

**Endpoint:** `POST /api/v1/generate-sms-link`

#### Request Body

```json
{
  "gstin": "29AABCU9603R1ZX",
  "gst_type": "3B",
  "period": "012026"
}
```

| Field      | Type   | Required | Description        | Validation                   |
| ---------- | ------ | -------- | ------------------ | ---------------------------- |
| `gstin`    | string | ✅ Yes   | 15-character GSTIN | Same format as Step 1        |
| `gst_type` | string | ✅ Yes   | GST return type    | Must be "3B", "R1", or "C8"  |
| `period`   | string | ✅ Yes   | Filing period      | MMYYYY format (e.g., 012026) |

#### Response - Success

```json
{
  "success": true,
  "sms_link": "https://sm-snacc.vercel.app/s/YeLFn6hA",
  "sms_preview": "NIL 3B 29AABCU9603R1ZX 012026",
  "instruction": "📱 Click the link below to send the SMS from your GST-registered mobile number.\n\n⚠️ Do NOT edit the SMS content.",
  "warning": "⚠️ Important:\n• Send from your GST-registered mobile ONLY\n• Do NOT modify the SMS text\n• You'll receive an OTP within 30-120 seconds",
  "error": null
}
```

| Field         | Type           | Description                       |
| ------------- | -------------- | --------------------------------- |
| `success`     | boolean        | Whether link generation succeeded |
| `sms_link`    | string         | Clickable deep link to send SMS   |
| `sms_preview` | string         | Preview of SMS text               |
| `instruction` | string         | User instructions                 |
| `warning`     | string         | Important warnings                |
| `error`       | string \| null | Error message if failed           |

#### Response - Error

```json
{
  "success": false,
  "sms_link": null,
  "sms_preview": null,
  "instruction": null,
  "warning": null,
  "error": "Failed to generate SMS link"
}
```

#### cURL Example

```bash
curl -X POST http://localhost:8001/api/v1/generate-sms-link \
  -H "Content-Type: application/json" \
  -d '{
    "gstin": "29AABCU9603R1ZX",
    "gst_type": "3B",
    "period": "012026"
  }'
```

#### Python Example

```python
import requests

response = requests.post(
    "http://localhost:8001/api/v1/generate-sms-link",
    json={
        "gstin": "29AABCU9603R1ZX",
        "gst_type": "3B",
        "period": "012026"
    }
)
result = response.json()

if result["success"]:
    print(f"SMS Link: {result['sms_link']}")
    print(f"SMS Preview: {result['sms_preview']}")
    print(f"\nInstructions:\n{result['instruction']}")
    print(f"\nWarning:\n{result['warning']}")
else:
    print(f"Error: {result['error']}")
```

---

### 4. Track Completion

Tracks filing completion for analytics and user records.

**Endpoint:** `POST /api/v1/track-completion`

#### Request Body

```json
{
  "phone": "+919876543210",
  "gstin": "29AABCU9603R1ZX",
  "gst_type": "3B",
  "period": "012026",
  "status": "completed"
}
```

| Field      | Type   | Required | Description         | Validation                  |
| ---------- | ------ | -------- | ------------------- | --------------------------- |
| `phone`    | string | ✅ Yes   | User's phone number | Any format                  |
| `gstin`    | string | ✅ Yes   | 15-character GSTIN  | Same format as Step 1       |
| `gst_type` | string | ✅ Yes   | GST return type     | Must be "3B", "R1", or "C8" |
| `period`   | string | ✅ Yes   | Filing period       | MMYYYY format               |
| `status`   | string | ✅ Yes   | Filing status       | "completed" or "failed"     |

#### Response - Success (Completed)

```json
{
  "tracked": true,
  "message": "🎉 Your filing has been recorded successfully!\n\nThank you for using NilEasy GST Filing Assistant.",
  "error": null
}
```

#### Response - Success (Failed)

```json
{
  "tracked": true,
  "message": "We've recorded your filing attempt.\n\nIf you need assistance, please try again or contact support.",
  "error": null
}
```

| Field     | Type           | Description                    |
| --------- | -------------- | ------------------------------ |
| `tracked` | boolean        | Whether tracking succeeded     |
| `message` | string         | Success/acknowledgment message |
| `error`   | string \| null | Error message if failed        |

#### Response - Error

```json
{
  "tracked": false,
  "message": null,
  "error": "Failed to track completion. Your filing may still be successful."
}
```

#### cURL Example

```bash
curl -X POST http://localhost:8001/api/v1/track-completion \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+919876543210",
    "gstin": "29AABCU9603R1ZX",
    "gst_type": "3B",
    "period": "012026",
    "status": "completed"
  }'
```

#### Python Example

```python
import requests

response = requests.post(
    "http://localhost:8001/api/v1/track-completion",
    json={
        "phone": "+919876543210",
        "gstin": "29AABCU9603R1ZX",
        "gst_type": "3B",
        "period": "012026",
        "status": "completed"
    }
)
result = response.json()

if result["tracked"]:
    print(result["message"])
else:
    print(f"Error: {result['error']}")
```

---

### 5. Health Check

System health check endpoint for monitoring.

**Endpoint:** `GET /api/v1/health`

#### Request

No request body required.

#### Response

```json
{
  "status": "healthy",
  "service": "NilEasy AiSensy API",
  "timestamp": "2026-02-04T10:30:45.123456",
  "endpoints": {
    "validate-gstin": "POST /api/v1/validate-gstin",
    "verify-captcha": "POST /api/v1/verify-captcha",
    "generate-sms-link": "POST /api/v1/generate-sms-link",
    "track-completion": "POST /api/v1/track-completion"
  }
}
```

#### cURL Example

```bash
curl http://localhost:8001/api/v1/health
```

---

## Complete Flow Example

Here's a complete end-to-end flow using Python:

```python
import requests

BASE_URL = "http://localhost:8001/api/v1"
GSTIN = "29AABCU9603R1ZX"

# Step 1: Validate GSTIN and fetch captcha
print("Step 1: Validating GSTIN...")
response = requests.post(
    f"{BASE_URL}/validate-gstin",
    json={"gstin": GSTIN}
)
result = response.json()

if not result["valid"]:
    print(f"Error: {result['error']}")
    exit(1)

captcha_url = result["captcha_url"]
session_id = result["session_id"]
print(f"✅ Captcha URL: {captcha_url}")
print(f"✅ Session ID: {session_id}")

# Step 2: Solve captcha manually (user opens captcha_url in browser)
captcha_text = input("\nEnter captcha text from image: ")

print("\nStep 2: Verifying captcha...")
response = requests.post(
    f"{BASE_URL}/verify-captcha",
    json={
        "session_id": session_id,
        "gstin": GSTIN,
        "captcha": captcha_text
    }
)
result = response.json()

if not result["success"]:
    print(f"Error: {result['error']}")
    exit(1)

details = result["business_details"]
print(f"\n✅ Business Details:")
print(f"   Name: {details['business_name']}")
print(f"   Legal Name: {details['legal_name']}")
print(f"   Address: {details['address']}")
print(f"   Status: {details['status']}")

# Step 3: Generate SMS link
print("\nStep 3: Generating SMS link...")
response = requests.post(
    f"{BASE_URL}/generate-sms-link",
    json={
        "gstin": GSTIN,
        "gst_type": "3B",
        "period": "012026"
    }
)
result = response.json()

if not result["success"]:
    print(f"Error: {result['error']}")
    exit(1)

print(f"\n✅ SMS Link: {result['sms_link']}")
print(f"✅ SMS Preview: {result['sms_preview']}")
print(f"\n{result['instruction']}")
print(f"\n{result['warning']}")

# Step 4: Track completion
print("\nStep 4: Tracking completion...")
response = requests.post(
    f"{BASE_URL}/track-completion",
    json={
        "phone": "+919876543210",
        "gstin": GSTIN,
        "gst_type": "3B",
        "period": "012026",
        "status": "completed"
    }
)
result = response.json()

if result["tracked"]:
    print(f"\n✅ {result['message']}")
else:
    print(f"Error: {result['error']}")
```

---

## Testing

### Interactive Test Script

Run the provided test script to walk through the entire flow:

```bash
python test_complete_flow.py
```

This script will:

1. Prompt for GSTIN input
2. Display captcha URL
3. Accept captcha text
4. Show business details
5. Accept GST type and period
6. Generate SMS link
7. Track completion

### Manual Testing with cURL

#### Test 1: Validate GSTIN

```bash
curl -X POST http://localhost:8001/api/v1/validate-gstin \
  -H "Content-Type: application/json" \
  -d '{"gstin": "29AABCU9603R1ZX"}'
```

#### Test 2: Verify Captcha

```bash
# Replace session_id and captcha with actual values
curl -X POST http://localhost:8001/api/v1/verify-captcha \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID",
    "gstin": "29AABCU9603R1ZX",
    "captcha": "ABC123"
  }'
```

#### Test 3: Generate SMS Link

```bash
curl -X POST http://localhost:8001/api/v1/generate-sms-link \
  -H "Content-Type: application/json" \
  -d '{
    "gstin": "29AABCU9603R1ZX",
    "gst_type": "3B",
    "period": "012026"
  }'
```

#### Test 4: Track Completion

```bash
curl -X POST http://localhost:8001/api/v1/track-completion \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+919876543210",
    "gstin": "29AABCU9603R1ZX",
    "gst_type": "3B",
    "period": "012026",
    "status": "completed"
  }'
```

#### Test 5: Health Check

```bash
curl http://localhost:8001/api/v1/health
```

### Automated Testing

Run unit tests (if available):

```bash
pytest tests/
```

---

## API Response Codes

| HTTP Code | Meaning               | Usage in NilEasy                         |
| --------- | --------------------- | ---------------------------------------- |
| 200       | Success               | All responses (including errors in body) |
| 422       | Validation Error      | Pydantic validation failures             |
| 500       | Internal Server Error | Unexpected server errors                 |

**Note:** All business logic errors return HTTP 200 with error details in response body for easier AiSensy integration.

---

## Data Models

### GSTIN Format

**Pattern:** `^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$`

**Example:** `29AABCU9603R1ZX`

**Breakdown:**

- First 2 digits: State code (29 = Karnataka)
- Next 5 characters: PAN first 5 characters
- Next 4 digits: Registration number
- Next 1 character: Entity code
- Next 1 character: Z (default)
- Last 1 character: Check digit

### Period Format

**Pattern:** `^(0[1-9]|1[0-2])(19|20)\d{2}$`

**Format:** MMYYYY

**Examples:**

- `012026` = January 2026
- `022025` = February 2025
- `122024` = December 2024

### GST Types

| Code | Full Form | Description                         | SMS Format Example            |
| ---- | --------- | ----------------------------------- | ----------------------------- |
| 3B   | GSTR-3B   | Monthly return for all taxpayers    | NIL 3B 29AABCU9603R1ZX 012026 |
| R1   | GSTR-1    | Details of outward supplies         | NIL R1 29AABCU9603R1ZX 012026 |
| C8   | CMP-08    | Composition scheme quarterly return | NIL C8 29AABCU9603R1ZX 062020 |

---

## Database Collections

### users Collection

```json
{
  "_id": "ObjectId",
  "phone": "+919876543210",
  "gstin": "29AABCU9603R1ZX",
  "business_name": "ETERNAL LIMITED",
  "last_filing_status": "completed",
  "created_at": "2026-02-04T10:30:45.123456",
  "updated_at": "2026-02-04T10:30:45.123456"
}
```

### filings Collection

```json
{
  "_id": "ObjectId",
  "phone": "+919876543210",
  "gstin": "29AABCU9603R1ZX",
  "gst_type": "3B",
  "period": "012026",
  "status": "completed",
  "timestamp": "2026-02-04T10:30:45.123456"
}
```

---

**Last Updated:** February 4, 2026  
**API Version:** 1.0.0  
**Maintained By:** NilEasy Team
