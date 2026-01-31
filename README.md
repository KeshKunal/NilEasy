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


