"""
app/api/aisensy.py

AiSensy Integration API Endpoints
==================================

Production-grade stateless API endpoints for WhatsApp Flow Builder integration.
These endpoints are called by AiSensy API Cards at specific validation points.


Architecture:
- No session state stored (stateless)
- Each endpoint is independent
- GST sessions stored in-memory with TTL
- Full request validation via Pydantic
- User-friendly error messages
- Production logging for debugging
- Unified user schema with embedded filings and generated_links
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any
import logging
import secrets
import string
from datetime import datetime, timedelta
from collections import defaultdict

from app.schemas.aisensy import (
    ValidateGSTINRequest,
    ValidateGSTINResponse,
    VerifyCaptchaRequest,
    VerifyCaptchaResponse,

    GenerateSMSLinkRequest,
    GenerateSMSLinkResponse,
    TrackCompletionRequest,
    TrackCompletionResponse
)
from app.services.gst_service import GSTService, GSTServiceError
from app.services.sms_link_service import SMSLinkService
from app.services.user_service import UserService
from app.db.mongo import get_database
from app.core.config import settings

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/v1", tags=["AiSensy"])

# Initialize services
gst_service = GSTService()
sms_service = SMSLinkService()

# Rate limiting storage (in-memory for simplicity)
# Production: Move to Redis with TTL
captcha_attempts: Dict[str, list] = defaultdict(list)
MAX_CAPTCHA_ATTEMPTS = 3
ATTEMPT_WINDOW = 3600  # 1 hour in seconds


async def get_user_service() -> UserService:
    """Get UserService instance with database connection."""
    db = await get_database()
    return UserService(db)


def check_rate_limit(gstin: str) -> tuple[bool, str]:
    """
    Check if GSTIN has exceeded captcha attempt rate limit.
    
    Returns:
        (is_allowed, error_message)
    """
    now = datetime.now()
    
    # Clean old attempts (older than 1 hour)
    captcha_attempts[gstin] = [
        attempt_time for attempt_time in captcha_attempts[gstin]
        if (now - attempt_time).total_seconds() < ATTEMPT_WINDOW
    ]
    
    # Check if limit exceeded
    if len(captcha_attempts[gstin]) >= MAX_CAPTCHA_ATTEMPTS:
        remaining_time = ATTEMPT_WINDOW - (now - captcha_attempts[gstin][0]).total_seconds()
        minutes = int(remaining_time / 60)
        return False, f"Too many attempts. Please try again in {minutes} minutes."
    
    return True, ""


def record_attempt(gstin: str):
    """Record a captcha attempt for rate limiting."""
    captcha_attempts[gstin].append(datetime.now())


# ============================================================================
# ENDPOINT 1: Validate GSTIN & Fetch Captcha
# ============================================================================

@router.post("/validate-gstin", response_model=ValidateGSTINResponse)
async def validate_gstin(request: ValidateGSTINRequest) -> ValidateGSTINResponse:
    """
    Validate GSTIN format and fetch captcha from GST portal.
    
    This is the first API call in the flow.
    AiSensy calls this when user enters GSTIN.
    
    Flow:
    1. Validate GSTIN format (handled by Pydantic)
    2. Check rate limiting
    3. Fetch captcha from GST portal
    4. Return captcha URL and session ID
    
    Returns:
        ValidateGSTINResponse with captcha_url and session_id
    """
    try:
        gstin = request.gstin
        phone = request.phone
        logger.info(f"Validating GSTIN: {gstin} for Phone: {phone}")

        # Save phone number link to GSTIN immediately if phone is provided
        if phone:
            user_service = await get_user_service()
            await user_service.update_or_create_user(
                user_id=gstin,
                gstin=gstin,
                phone=phone,
                last_updated_status="Initiated"
            )
        
        # Check rate limiting
        is_allowed, error_msg = check_rate_limit(gstin)
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for GSTIN: {gstin}")
            return ValidateGSTINResponse(
                valid=False,
                error=error_msg
            )
            
        # Check if GSTIN already exists in DB
        user_service = await get_user_service()
        logger.info(f"Checking DB for existing GSTIN: {gstin}")
        existing_user = await user_service.get_user_by_gstin(gstin)
        
        if existing_user:
            logger.info(f"Found user for GSTIN {gstin}: {existing_user.get('_id')}")
            biz_name = existing_user.get("business_name")
            biz_address = existing_user.get("address")
            if biz_name and biz_name != "N/A":
                logger.info(f"GSTIN found in database with business name: {biz_name}")
                return ValidateGSTINResponse(
                    valid="found",
                    captcha_url=biz_name,
                    session_id=biz_address if biz_address and biz_address != "N/A" else None
                )
            else:
                logger.warning(f"User found for GSTIN {gstin} but no business_name present")
        else:
            logger.info(f"No existing user found for GSTIN: {gstin}")
        
        # Record attempt
        record_attempt(gstin)
        
        # Fetch captcha from GST portal
        result = await gst_service.get_captcha(gstin)
        
        # gst_service.get_captcha returns {"session_id": ..., "image": user_id}
        if not result.get('session_id'):
            logger.error(f"Failed to fetch captcha for {gstin}")
            return ValidateGSTINResponse(
                valid=False,
                error='Failed to fetch captcha from GST portal'
            )
        
        # Build captcha URL using the captcha endpoint
        # Add a random fragment to prevent caching and ensure unique URL for client
        random_fragment = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(6))
        captcha_url = f"{settings.APP_URL}/api/v1/captcha/{result['image']}#{random_fragment}"
        
        logger.info(f"Captcha fetched successfully for {gstin}")
        return ValidateGSTINResponse(
            valid=True,
            captcha_url=captcha_url,
            session_id=result['session_id']
        )
        
    except GSTServiceError as e:
        logger.warning(f"GST service error in validate_gstin: {str(e)}")
        return ValidateGSTINResponse(
            valid=False,
            error=str(e)
        )
    except Exception as e:
        logger.exception(f"Unexpected error in validate_gstin: {str(e)}")
        return ValidateGSTINResponse(
            valid=False,
            error="An unexpected error occurred. Please try again."
        )


# ============================================================================
# ENDPOINT 2: Verify Captcha & Get Business Details
# ============================================================================

@router.post("/verify-captcha", response_model=VerifyCaptchaResponse)
async def verify_captcha(request: VerifyCaptchaRequest) -> VerifyCaptchaResponse:
    """
    Verify captcha and fetch business details from GST portal.
    
    This is the second API call in the flow.
    AiSensy calls this when user submits captcha text.
    
    Flow:
    1. Verify captcha against GST portal
    2. Fetch business details if captcha is correct
    3. Return business details for user confirmation
    
    Returns:
        VerifyCaptchaResponse with business_details
    """
    try:
        logger.info(f"Verifying captcha for GSTIN: {request.gstin}")
        
        # Verify captcha and get business details
        result = await gst_service.verify_gstin(
            user_id=request.gstin,  # Using GSTIN as temp user ID
            gstin=request.gstin,
            captcha=request.captcha,
            session_id=request.session_id
        )
        
        if not result['success']:
            error_msg = result.get('error', 'Invalid captcha or GSTIN verification failed')
            logger.warning(f"Captcha verification failed for {request.gstin}: {error_msg}")
            
            # Update status to "Verifying captcha" on failure
            user_service = await get_user_service()
            await user_service.update_or_create_user(
                user_id=request.gstin,
                gstin=request.gstin,
                last_updated_status="Verifying captcha"
            )
            
            return VerifyCaptchaResponse(
                success=False,
                error=error_msg
            )
        
        # Extract business details
        details = result.get('business_details', {})
        if not details:
            logger.error(f"No business details returned for {request.gstin}")
            return VerifyCaptchaResponse(
                success=False,
                error="Failed to fetch business details. Please try again."
            )
        
        # Save business details to user
        logger.info(f"Saving business details for GSTIN {request.gstin} to DB")
        user_service = await get_user_service()
        saved = await user_service.update_or_create_user(
            user_id=request.gstin,  # Using GSTIN as temp ID until phone is known
            gstin=request.gstin,
            business_name=details.get('trade_name', 'N/A'),
            address=details.get('address', 'N/A'),
            last_updated_status="Onboarded"
        )
        logger.info(f"Business details saved: {saved}")

        
        # Build response with business details directly at root
        return VerifyCaptchaResponse(
            success=True,
            business_name=details.get('trade_name', 'N/A'),
            legal_name=details.get('legal_name', 'N/A'),
            address=details.get('address', 'N/A'),
            registration_date=details.get('registration_date', 'N/A'),
            status=details.get('status', 'N/A'),
            gstin=request.gstin
        )
        
    except GSTServiceError as e:
        logger.warning(f"GST service error in verify_captcha: {str(e)}")
        return VerifyCaptchaResponse(
            success=False,
            error=str(e)
        )
    except Exception as e:
        logger.exception(f"Unexpected error in verify_captcha: {str(e)}")
        return VerifyCaptchaResponse(
            success=False,
            error="An unexpected error occurred. Please try again."
        )


# ============================================================================
# ENDPOINT 3: Generate SMS Link
# ============================================================================

@router.post("/generate-sms-link", response_model=GenerateSMSLinkResponse)
async def generate_sms_link(request: GenerateSMSLinkRequest) -> GenerateSMSLinkResponse:
    """
    Generate SMS deep link for GST filing.
    
    This is the third API call in the flow.
    AiSensy calls this after user selects GST type and period.
    
    Flow:
    1. Validate inputs (handled by Pydantic)
    2. Format SMS text (NIL <type> <GSTIN> <period>)
    3. Generate deep link using SMS shortlink service
    4. Save generated link to user's generated_links array
    5. Return clickable link with preview and instructions
    
    Returns:
        GenerateSMSLinkResponse with sms_link and instructions
    """
    try:
        logger.info(
            f"Generating SMS link for GSTIN: {request.gstin}, "
            f"Type: {request.gst_type}, Period: {request.period}"
        )
        
        # Format SMS text
        sms_text = f"NIL {request.gst_type} {request.gstin} {request.period}"
        
        # Generate deep link
        result = await sms_service.create_sms_deep_link(
            sms_text=sms_text,
            phone_number=settings.GST_FILING_NUMBER,  # GST filing number
            user_phone=""  # Not needed for this flow
        )
        
        # Get user service for saving data
        user_service = await get_user_service()
        
        # Save filing context for later tracking
        await user_service.save_filing_context(
            gstin=request.gstin,
            gst_type=request.gst_type,
            period=request.period
        )
        
        # Update status to "SMS GENERATED"
        # We don't have phone here, so key by GSTIN
        await user_service.update_or_create_user(
            user_id=request.gstin,
            gstin=request.gstin,
            last_updated_status="SMS GENERATED"
        )
        
        # sms_link_service returns {"success": bool, "short_url": str, ...}
        if not result.get('success'):
            error_msg = result.get('error', 'Failed to generate SMS link')
            logger.error(f"SMS link generation failed: {error_msg}")
            return GenerateSMSLinkResponse(
                success=False,
                error=error_msg
            )
        
        short_url = result.get('short_url', '')
        short_code = result.get('short_code', '')
        
        # Save generated link to user's generated_links array
        await user_service.add_generated_link(
            phone=None,  # Phone not known yet
            short_url=short_url,
            short_code=short_code,
            sms_text=sms_text,
            gstin=request.gstin,
            gst_type=request.gst_type,
            period=request.period
        )
        
        logger.info(f"SMS link generated and saved for {request.gstin}")
        
        return GenerateSMSLinkResponse(
            success=True,
            sms_link=short_url,
            sms_preview=sms_text,
            instruction=(
                "📱 Click the link below to send the SMS from your "
                "GST-registered mobile number.\n\n"
                "⚠️ Do NOT edit the SMS content."
            ),
            warning=(
                "⚠️ Important:\n"
                "• Send from your GST-registered mobile ONLY\n"
                "• Do NOT modify the SMS text\n"
                "• You'll receive an OTP within 30-120 seconds"
            )
        )
        
    except Exception as e:
        logger.exception(f"Unexpected error in generate_sms_link: {str(e)}")
        return GenerateSMSLinkResponse(
            success=False,
            error="An unexpected error occurred. Please try again."
        )


# ============================================================================
# ENDPOINT 4: Track Completion
# ============================================================================

@router.post("/track-completion", response_model=TrackCompletionResponse)
async def track_completion(request: TrackCompletionRequest) -> TrackCompletionResponse:
    """
    Track filing completion for analytics.
    
    This is the fourth API call in the flow.
    AiSensy calls this when user confirms successful filing or reports failure.
    
    Flow:
    1. Store completion/failure record in user's embedded filings array
    2. Update user analytics
    3. Return confirmation
    
    Returns:
        TrackCompletionResponse with tracking confirmation
    """
    try:
        logger.info(
            f"Tracking completion for phone: {request.phone}, "
            f"GSTIN: {request.gstin}, Status: {request.status}"
        )
        
        # Get user service
        user_service = await get_user_service()
        
        # Retrieve filing context
        context = await user_service.get_filing_context(request.gstin)
        
        # Default values if context is missing (should not happen in normal flow)
        gst_type = context.get('gst_type') if context else 'UNKNOWN'
        period = context.get('period') if context else 'UNKNOWN'
        
        if not context:
            logger.warning(f"Filing context missing for GSTIN: {request.gstin}")
        
        # Add filing to user's embedded filings array
        await user_service.add_filing(
            phone=request.phone,
            gstin=request.gstin,
            gst_type=gst_type,
            period=period,
            status=request.status
        )
        
        # Update user record (create if doesn't exist)
        
        updates = {
             "user_id": request.gstin,
             "gstin": request.gstin,
             "last_filing_status": request.status
        }
        
        if request.status == 'completed':
            updates["last_updated_status"] = "FILING DONE"
            
        # Pass phone explicitly to ensure it updates/saves
        updates["phone"] = request.phone
            
        await user_service.update_or_create_user(**updates)
        
        logger.info(f"Filing tracked successfully for {request.phone}")
        
        if request.status == 'completed':
            message = (
                "🎉 Your filing has been recorded successfully!\n\n"
                "Thank you for using NilEasy GST Filing Assistant."
            )
        else:
            message = (
                "We've recorded your filing attempt.\n\n"
                "If you need assistance, please try again or contact support."
            )
        
        return TrackCompletionResponse(
            tracked=True,
            message=message
        )
        
    except Exception as e:
        logger.exception(f"Unexpected error in track_completion: {str(e)}")
        return TrackCompletionResponse(
            tracked=False,
            error="Failed to track completion. Your filing may still be successful."
        )


# ============================================================================
# Health Check Endpoint
# ============================================================================

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for monitoring.
    
    Returns:
        Service status and timestamp
    """
    return {
        "status": "healthy",
        "service": "NilEasy AiSensy API",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "validate-gstin": "POST /api/v1/validate-gstin",
            "verify-captcha": "POST /api/v1/verify-captcha",
            "generate-sms-link": "POST /api/v1/generate-sms-link",
            "track-completion": "POST /api/v1/track-completion"
        }
    }
