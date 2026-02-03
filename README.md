# NilEasy - WhatsApp-based GST Nil Filing Assistant

An intelligent WhatsApp chatbot that guides users through the GST Nil filing process step-by-step.

## Project Structure
```
NilEasy/
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   └── webhook.py
│   │
│   ├── flow/
│   │   ├── states.py
│   │   ├── dispatcher.py
│   │   └── handlers/
│   │       ├── welcome.py
│   │       ├── gstin.py
│   │       ├── captcha.py
│   │       ├── gst_type.py
│   │       ├── duration.py
│   │       ├── sms.py
│   │       ├── otp.py
│   │       └── completion.py
│   │
│   ├── services/
│   │   ├── user_service.py
│   │   ├── session_service.py
│   │   ├── gst_service.py
│   │   ├── sms_service.py
│   │   └── filing_service.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   └── filing_attempt.py
│   │
│   ├── schemas/
│   │   ├── webhook.py
│   │   └── user.py
│   │
│   ├── db/
│   │   ├── mongo.py
│   │   └── indexes.py
│   │
│   └── core/
│       ├── config.py
│       └── logging.py
│
├── utils/
│   ├── whatsapp_utils.py
│   ├── gst_utils.py
│   ├── sms_utils.py
│   ├── validation_utils.py
│   ├── time_utils.py
│   └── constants.py
│
├── tests/
│
├── .env.example
├── requirements.txt
└── README.md

```

## Features

- 🤖 Conversational GST filing via WhatsApp
- ✅ GSTIN validation and verification
- 📱 SMS-based OTP workflow
- 🔄 State-managed conversation flow
- 📊 Filing audit trail
- 🛡️ Session management and validation

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and configure
3. Install dependencies: `pip install -r requirements.txt`
4. Run the application: `uvicorn app.main:app --reload`

## Architecture

This application follows a clean, modular architecture:

- **Flow Handlers**: Each conversation step has its own handler
- **Services**: Business logic and external integrations
- **Models**: MongoDB document structures
- **Utils**: Reusable helper functions

# GST Nil Filing via WhatsApp

---

## Objective

Build a **guided WhatsApp-based assistant** that helps GST taxpayers successfully file **Nil returns via SMS**, with minimal errors, using WhatsApp Business API (AiSensy) for structured interaction, validation, and follow-ups.

---

## Conversation Model

> Single entry point + state-driven flow
> 
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
> 
> We’ll help you file your Nil return via the official SMS method.
> 

Button:

- 👉 Start Nil Filing
- ℹ️ How this works

---

### 🔹 STEP 1: Ask GSTIN

**Text Input**

> Please enter your 15-digit GSTIN
> 

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
> 
> Business Name: ___
> 
> State: ___
> 

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

ℹ️ *Info option shows short explanation, then returns to list*

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
> 

Buttons:

- ✅ SMS Sent
- ❌ I have an issue

State → `SMS_SENT_WAIT`

---

### 🔹 STEP 6: OTP Sent Confirmation

Bot:

> ⏳ You’ll receive an OTP from GST within 30–120 seconds.
> 

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
> 

Then soft promotion:

> 💡 Need help with loans, compliance, or growth?
> 
> 
> Check out **ASPIRE** products designed for small businesses.
> 

Buttons:

- 🚀 Explore Aspire
- 🏁 Done

State → `COMPLETED`

---

## AiSensy-Specific Work Breakdown

### 🔧 Backend Team

- Webhook handling
- State management
- GST APIs
- SMS link generation
- OTP parsing (optional)

### 💬 WhatsApp / AiSensy Setup

- Message templates approval
- Button & list configurations
- Session window handling (24-hour rule)
- Fallback templates

### 🧠 Product / UX

- Exact wording of messages
- Error & retry copy
- Trust signals
- Promotion placement

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

---

## File Structure:

```jsx
NilEasy/
│
├── app/
│   ├── [main.py](http://main.py/)
│   │
│   ├── api/
│   │   └── [webhook.py](http://webhook.py/)
│   │
│   ├── flow/
│   │   ├── [states.py](http://states.py/)
│   │   ├── [dispatcher.py](http://dispatcher.py/)
│   │   └── handlers/
│   │       ├── [welcome.py](http://welcome.py/)
│   │       ├── [gstin.py](http://gstin.py/)
│   │       ├── [captcha.py](http://captcha.py/)
│   │       ├── gst_type.py
│   │       ├── [duration.py](http://duration.py/)
│   │       ├── [sms.py](http://sms.py/)
│   │       ├── [otp.py](http://otp.py/)
│   │       └── [completion.py](http://completion.py/)
│   │
│   ├── services/
│   │   ├── user_service.py
│   │   ├── session_service.py
│   │   ├── gst_service.py
│   │   ├── sms_service.py
│   │   └── filing_service.py
│   │
│   ├── models/
│   │   ├── [user.py](http://user.py/)
│   │   └── filing_attempt.py
│   │
│   ├── schemas/
│   │   ├── [webhook.py](http://webhook.py/)
│   │   └── [user.py](http://user.py/)
│   │
│   ├── db/
│   │   ├── [mongo.py](http://mongo.py/)
│   │   └── [indexes.py](http://indexes.py/)
│   │
│   └── core/
│       ├── [config.py](http://config.py/)
│       └── [logging.py](http://logging.py/)
│
├── utils/
│   ├── whatsapp_utils.py
│   ├── gst_utils.py
│   ├── sms_utils.py
│   ├── validation_utils.py
│   ├── time_utils.py
│   └── [constants.py](http://constants.py/)
│
├── tests/
│
├── .env.example
├── requirements.txt
└── [README.md](http://readme.md/)
```

# 📁 Description

---

## 📁 app/

Core application code.

Contains all business logic, flow control, and integrations.

---

### `app/main.py`

**Purpose:** Application entry point

- Initializes FastAPI app
- Loads configuration and logging
- Registers API routes (webhook)
- No business logic should be written here

---

## 📁 app/api/

### `app/api/webhook.py`

**Purpose:** Single WhatsApp webhook endpoint

- Receives incoming WhatsApp/AiSensy events
- Parses message payloads
- Passes control to the flow dispatcher
- Returns WhatsApp-compatible responses

---

## 📁 app/flow/

Handles **conversation flow and state transitions**.

### `app/flow/states.py`

**Purpose:** Defines all conversation states

- Enum or constants for each step in the flow
    
    (WELCOME, ASK_GSTIN, GST_VERIFIED, OTP_RECEIVED, COMPLETED, etc.)
    
- Single source of truth for flow stages

---

### `app/flow/dispatcher.py`

**Purpose:** Central flow router

- Reads the user’s `current_state`
- Dispatches incoming input to the correct handler
- Prevents invalid state transitions
- Ensures users cannot skip steps

---

### 📁 app/flow/handlers/

Each file handles **exactly one step** in the chat flow.

---

### `welcome.py`

**Handles:** STEP 0 – Entry / Welcome

- Processes “Hi” / CTA entry
- Sends welcome message and start options
- Initializes session state

---

### `gstin.py`

**Handles:** STEP 1 – Ask GSTIN

- Accepts GSTIN input
- Validates format (via utils)
- Handles retry on invalid GSTIN
- Stores GSTIN in temporary session data

---

### `captcha.py`

**Handles:** STEP 2 – Captcha & GST detail verification

- Calls GST services using GSTIN + captcha
- Displays extracted business details
- Handles user confirmation or rejection
- Rolls back to GSTIN step if rejected

---

### `gst_type.py`

**Handles:** STEP 3 – GST Return Type selection

- Displays WhatsApp list (GSTR-1, GSTR-3B)
- Handles info/help option
- Saves selected return type

---

### `duration.py`

**Handles:** STEP 4 – Filing duration selection

- Monthly / Quarterly selection
- Month or quarter mapping
- Normalizes period into GST-accepted format
- Stores duration in session data

---

### `sms.py`

**Handles:** STEP 5 – SMS generation & confirmation

- Generates exact GST SMS content
- Creates deep link to messaging app
- Displays warnings not to edit SMS
- Tracks user confirmation of SMS sent

---

### `otp.py`

**Handles:** STEP 6 & 7 – OTP and confirmation

- Handles OTP received / not received flows
- Extracts OTP from pasted messages (optional)
- Generates confirmation SMS format
- Handles retries and troubleshooting paths

---

### `completion.py`

**Handles:** STEP 8 – Success & promotion

- Confirms successful filing (ARN received)
- Sends success message
- Promotes Aspire products
- Ends or resets the session

---

## 📁 app/services/

Contains **business logic and external integrations**.

Handlers should call services; services never call handlers.

---

### `user_service.py`

**Purpose:** User data management

- Create or update user records
- Persist GSTIN and business details
- Update user state and metadata

---

### `session_service.py`

**Purpose:** Session and state management

- Updates `current_state`
- Tracks last interaction time
- Handles session expiry and reset logic
- Enforces valid state transitions

---

### `gst_service.py`

**Purpose:** GST system integration

- Handles GSTIN verification
- Captcha handling
- Fetches business details from GST APIs
- Abstracts GST logic from flow handlers

---

### `sms_service.py`

**Purpose:** SMS workflow logic

- Coordinates SMS generation steps
- Tracks SMS send/confirmation lifecycle
- Manages retries and failures

---

### `filing_service.py`

**Purpose:** Nil filing lifecycle management

- Tracks filing attempts
- Stores OTP/ARN timestamps
- Updates filing status (initiated, confirmed, failed)
- Provides auditability for compliance

---

## 📁 app/models/

Defines database document structures (MongoDB).

---

### `user.py`

**Purpose:** User document model

- Telegram/WhatsApp ID
- GSTIN and business details
- Current state and session metadata
- Temporary data and short-link info

---

### `filing_attempt.py`

**Purpose:** Filing audit model

- Tracks each Nil filing attempt
- Stores GST type, period, status
- Records OTP and ARN timestamps
- Used for retries, debugging, and analytics

---

## 📁 app/schemas/

Pydantic models for validation and serialization.

---

### `webhook.py`

**Purpose:** WhatsApp webhook payload schemas

- Validates incoming AiSensy messages
- Ensures predictable request handling

---

### `user.py`

**Purpose:** User-related request/response schemas

- Used by services and handlers
- Prevents invalid data propagation

---

## 📁 app/db/

Database configuration and setup.

---

### `mongo.py`

**Purpose:** MongoDB connection setup

- Initializes Motor client
- Exposes database and collections
- Centralized DB access point

---

### `indexes.py`

**Purpose:** Database index management

- Creates unique and performance indexes
- Ensures fast lookups and data integrity

---

## 📁 app/core/

Core infrastructure configuration.

---

### `config.py`

**Purpose:** Application configuration

- Loads environment variables
- Centralizes config values (DB URI, secrets, etc.)

---

### `logging.py`

**Purpose:** Logging configuration

- Standardizes log format
- Controls log levels
- Enables observability in production

---

## 📁 utils/

Shared stateless helper functions.

---

### `whatsapp_utils.py`

**Purpose:** WhatsApp message builders

- Constructs button, list, and text payloads
- Abstracts WhatsApp API formatting

---

### `gst_utils.py`

**Purpose:** GST-specific helpers

- GSTIN formatting and normalization
- Period formatting utilities

---

### `sms_utils.py`

**Purpose:** SMS formatting helpers

- Builds exact GST-compliant SMS text
- Generates deep links to messaging apps

---

### `validation_utils.py`

**Purpose:** Input validation

- GSTIN regex
- OTP parsing
- Date and period validation

---

### `time_utils.py`

**Purpose:** Time and expiry helpers

- Session TTL calculations
- OTP expiry checks
- Timestamp utilities

---

### `constants.py`

**Purpose:** Centralized static content

- All user-facing messages
- Button labels
- Reusable enums and constants
    
    *(Prevents hardcoding across the codebase)*
    

---

## 📁 tests/

**Purpose:** Automated testing

- Unit tests for services and handlers
- Integration tests for flow correctness
- Regression protection

---

## Root Files

### `.env.example`

- Template for environment variables
- No secrets committed

### `requirements.txt`

- Python dependencies

### `README.md`

- Project overview
- Setup instructions
- Architecture explanation

