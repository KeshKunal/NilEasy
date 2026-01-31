# NilEasy - WhatsApp-based GST Nil Filing Assistant

An intelligent WhatsApp chatbot that guides users through the GST Nil filing process step-by-step.

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

## Project Structure

See individual files for detailed documentation.
