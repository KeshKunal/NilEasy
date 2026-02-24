# NilEasy - WhatsApp-based GST Nil Filing Assistant

An intelligent WhatsApp chatbot that guides users through the GST Nil filing process via AiSensy Flow Builder integration.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your credentials

# Run the server
uvicorn app.main:app --reload --port 8001
```

Server will start at `http://localhost:8001`

## 📋 Architecture Overview

Stateless API endpoints for AiSensy Flow Builder  

### AiSensy Integration Flow

```
WhatsApp → AiSensy Flow Builder → API Cards → Our Backend (4 endpoints)
```

### API Endpoints

1. **POST /api/v1/validate-gstin** - Validate GSTIN & fetch captcha
2. **POST /api/v1/verify-captcha** - Verify captcha & get business details
3. **POST /api/v1/generate-sms-link** - Generate SMS deep link for filing
4. **POST /api/v1/track-completion** - Track filing completion for analytics
5. **GET /api/v1/health** - Health check endpoint

📚 **Complete API Documentation:** [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

## Project Structure

```
NilEasy/
│
├── app/
│   ├── main.py                  # FastAPI entry point
│   │
│   ├── api/
│   │   └── aisensy.py          # 4 AiSensy API endpoints
│   │
│   ├── services/
│   │   ├── user_service.py     # User & analytics management
│   │   ├── gst_service.py      # GST portal integration
│   │   └── sms_link_service.py # SMS shortlink generation
│   │
│   ├── schemas/
│   │   ├── aisensy.py          # Pydantic request/response models
│   │   └── user.py
│   │
│   ├── db/
│   │   ├── mongo.py            # MongoDB connection
│   │   └── indexes.py          # Database indexes
│   │
│   └── core/
│       ├── config.py           # Configuration
│       └── logging.py          # Logging setup
│
├── utils/                       # Helper functions
├── REFACTORING_GUIDE.md        # Complete API documentation
├── requirements.txt
└── README.md
```

## Features

- 🤖 **Stateless API Architecture** - No server-side sessions
- ✅ **GSTIN Validation** - Format checking + GST portal verification
- 🖼️ **Captcha Integration** - Direct GST portal captcha fetch
- 📱 **SMS Deep Links** - Automated SMS link generation to 14409
- 🔄 **Rate Limiting** - 3 captcha attempts per GSTIN per hour
- 📊 **Analytics Tracking** - Filing success/failure metrics
- 🛡️ **Production Ready** - Comprehensive error handling & logging

## Core Flow

1. User enters **GSTIN** → API validates format
2. System fetches **Captcha** from GST portal
3. User solves captcha → System fetches **Business Details**
4. User confirms details → Selects **GST Type** (3B/R1) & **Period**
5. System generates **SMS deep link** → User sends SMS to 14409
6. User receives **OTP** → Sends confirmation SMS
7. System tracks **completion** for analytics

## Setup

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd NilEasy
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**

   ```bash
   cp .env.example .env
   # Edit .env with your MongoDB URI and other credentials
   ```

4. **Run the application**

   ```bash
   uvicorn app.main:app --reload --port 8001
   ```

5. **Test the API**
   ```bash
   curl http://localhost:8001/api/v1/health
   ```

## Environment Variables

```env
# MongoDB
MONGODB_URL=mongodb+srv://...
MONGODB_DB_NAME=zerofactorial

# Application
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=INFO

# API Configuration
API_PREFIX=/api/v1
```

## API Documentation

For complete API documentation including:

- Request/Response schemas
- Authentication & Rate limiting
- Error handling
- Complete code examples in Python & cURL
- Interactive testing guide

Quick reference: [API_DOCUMENTATION.md](API_DOCUMENTATION.md)


## Architecture

This application follows a **stateless API architecture**:

- **API Endpoints**: 4 independent endpoints for AiSensy Flow Builder
- **Services**: Business logic and external integrations (GST portal, SMS)
- **Database**: MongoDB with optimized indexes for analytics
- **Utils**: Reusable validation and helper functions

### Key Design Decisions

1. **Stateless**: No server-side session management
2. **Rate Limited**: Prevents GST portal abuse
3. **Analytics First**: Track every filing attempt
4. **Error Friendly**: HTTP 200 with success flags for easier AiSensy integration
5. **Production Grade**: Comprehensive logging, error handling, and monitoring

## Database Collections

### users

- Primary key: `phone`
- Tracks: GSTIN, business details, filing statistics

### filings

- Tracks: Each filing attempt with status (completed/failed)
- Analytics: Success rates, period-wise filings

---

## Conversation Model

> Single entry point + state-driven flow

- No free-text commands
- Mostly button/list-based inputs
- Every message validated against `current_state`
- Users can never “jump steps”

---

## Final Chat Flow

### 🔹 STEP 0: Entry / Welcome

**Trigger**: User sends “Hi” / clicks CTA / incoming message

**Bot:**

> 👋 Welcome to GST Nil Filing Assistant
>
> We’ll help you file your Nil return via the official SMS method.

Button:

- 👉 Start Nil Filing
- ℹ️ How this works

---

### 🔹 STEP 1: Ask GSTIN

**Text Input**

> Please enter your 15-digit GSTIN

Validation:

- Format check (regex)
- If invalid → error + retry

State → `ASK_GSTIN`

---

### 🔹 STEP 2: Captcha Verification (Critical Step)

Backend:

- Fetch GST details using GSTIN + captcha
- Show extracted details:

**Bot:**

> 🔍 Please confirm your details:
>
> Business Name: \_\_\_
>
> State: \_\_\_

Buttons:

- ✅ Details are correct
- ❌ Incorrect details

❌ → Go back to GSTIN step

✅ → Proceed

State → `GST_VERIFIED`

### 🔹 STEP 3: Ask GST Return Type

**WhatsApp List Message**

- GSTR-1
- GSTR-3B

ℹ️ _Info option shows short explanation, then returns to list_

State → `ASK_GST_TYPE`

---

### 🔹 STEP 4: Ask Filing Duration

**WhatsApp List / Button**

- Monthly
- Quarterly
  → Followed by **month / quarter selection**

State → `ASK_DURATION`

---

### 🔹 STEP 5: Generate SMS Link + Confirmation

Bot sends:

- 📩 Pre-filled SMS link (deep link)
- SMS content shown in **monospace**
- Warning not to edit

**Bot:**

> ⚠️ Send this SMS from your GST-registered mobile number only

Buttons:

- ✅ SMS Sent
- ❌ I have an issue

State → `SMS_SENT_WAIT`

---

### 🔹 STEP 6: OTP Sent Confirmation

Bot:

> ⏳ You’ll receive an OTP from GST within 30–120 seconds.

Buttons:

- ✅ OTP Received
- ❌ Didn’t receive OTP

❌ → contextual troubleshooting

✅ → proceed

State → `OTP_RECEIVED`

---

### 🔹 STEP 7: Confirmation Received?

User pastes OTP message (optional).

Bot:

- Extract OTP
- Generate **confirmation SMS format**
- Provide clickable SMS link again

Buttons:

- ✅ Confirmation SMS Sent
- ❌ Need help

Then wait for ARN.

State → `CONFIRMATION_WAIT`

---

### 🔹 STEP 8: Success + Promotion

On ARN confirmation:

**Bot:**

> 🎉 Your Nil Return has been filed successfully!

Then soft promotion:

> 💡 Need help with loans, compliance, or growth?
>
> Check out **ASPIRE** products designed for small businesses.

Buttons:

- 🚀 Explore Aspire
- 🏁 Done

State → `COMPLETED`


---

## Error Handling & Recovery

- Session timeout → restart flow politely
- Wrong GSTIN → rollback state
- Wrong Captcha → fetch again
- OTP expired → regenerate SMS
- Multiple failures → show manual help option

---

## Compliance & Safety Notes

- We do **not** send SMS on user’s behalf
- We do **not** store OTP permanently
- We only assist, guide, and format
- Clear disclaimers at SMS steps
