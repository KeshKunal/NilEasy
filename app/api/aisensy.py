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
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any
import logging
from datetime import datetime, timedelta
from collections import defaultdict

from app.schemas.aisensy import (
    ValidateGSTINRequest,
    ValidateGSTINResponse,
    VerifyCaptchaRequest,
    VerifyCaptchaResponse,
    BusinessDetails,
    GenerateSMSLinkRequest,
    GenerateSMSLinkResponse,
    TrackCompletionRequest,
    TrackCompletionResponse
)
from app.services.gst_service import GSTService
from app.services.sms_link_service import SMSLinkService
from app.services.user_service import UserService
from app.services.filing_service import FilingService
from app.db.mongo import get_database
from app.core.config import settings

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/v1", tags=["AiSensy"])

# Initialize services
gst_service = GSTService()
sms_service = SMSLinkService()
filing_service = FilingService()

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
    2. Check users collection for cached GSTIN data
    3. If found, return business details (skip captcha)
    4. If not found, check rate limiting and fetch captcha
    5. Return captcha URL and session ID
    
    Returns:
        ValidateGSTINResponse with either business_details (cached) or captcha_url
    """
    try:
        gstin = request.gstin
        logger.info(f"Validating GSTIN: {gstin}")
        
        # Check users collection first for cached GSTIN data
        user_service = await get_user_service()
        cached_gst_data = await user_service.get_gstin_details(gstin)
        
        if cached_gst_data:
            logger.info(f"Returning cached details for GSTIN: {gstin}")
            
            # Return business details directly from cache (skip captcha)
            business_details = BusinessDetails(
                business_name=cached_gst_data.get('tradeNam', 'N/A'),
                legal_name=cached_gst_data.get('lgnm', 'N/A'),
                address=cached_gst_data.get('address', 'N/A'),
                registration_date=cached_gst_data.get('rgdt', 'N/A'),
                status=cached_gst_data.get('sts', 'N/A'),
                gstin=gstin
            )
            
            return ValidateGSTINResponse(
                valid=True,
                captcha_url=None,  # No captcha needed
                session_id="cached",  # Indicate this is from cache
                business_details=business_details
            )
        
        # Not in cache - proceed with normal captcha flow
        logger.info(f"GSTIN not in cache, fetching captcha: {gstin}")
        
        # Check rate limiting
        is_allowed, error_msg = check_rate_limit(gstin)
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for GSTIN: {gstin}")
            return ValidateGSTINResponse(
                valid=False,
                error=error_msg
            )
        
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
        
        # Build captcha URL using the captcha endpoint (use Railway URL in production)
        base_url = settings.APP_URL.rstrip('/')
        captcha_url = f"{base_url}/api/v1/captcha/{result['image']}"
        
        logger.info(f"Captcha fetched successfully for {gstin}")
        return ValidateGSTINResponse(
            valid=True,
            captcha_url=captcha_url,
            session_id=result['session_id']
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
        
        logger.info(f"Captcha verified successfully for {request.gstin}")
        
        # Build response with business details (user-facing subset)
        business_details = BusinessDetails(
            business_name=details.get('tradeNam', 'N/A'),
            legal_name=details.get('lgnm', 'N/A'),
            address=details.get('address', 'N/A'),
            registration_date=details.get('rgdt', 'N/A'),
            status=details.get('sts', 'N/A'),
            gstin=request.gstin
        )
        
        # Store COMPLETE GST data in users collection (store all, show subset)
        user_service = await get_user_service()
        await user_service.store_gst_data(
            phone=request.gstin,  # Using GSTIN as phone for now (will be updated when user provides phone)
            gst_data=details,  # Store complete data
            business_name=details.get('tradeNam', 'N/A')
        )
        logger.info(f"Stored complete GST data for {request.gstin}")
        
        return VerifyCaptchaResponse(
            success=True,
            business_details=business_details
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
    4. Return clickable link with preview and instructions
    
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
            phone_number="14409",  # GST filing number
            user_phone=""  # Not needed for this flow
        )
        
        # sms_link_service returns {"success": bool, "short_url": str, ...}
        if not result.get('success'):
            error_msg = result.get('error', 'Failed to generate SMS link')
            logger.error(f"SMS link generation failed: {error_msg}")
            return GenerateSMSLinkResponse(
                success=False,
                error=error_msg
            )
        
        logger.info(f"SMS link generated successfully for {request.gstin}")
        
        # Create filing attempt record for tracking
        try:
            await filing_service.create_filing_attempt(
                phone=request.gstin,  # Using GSTIN as identifier for now
                gstin=request.gstin,
                gst_type=request.gst_type,
                period=request.period,
                sms_link=result['short_url']
            )
        except Exception as e:
            logger.warning(f"Failed to create filing attempt: {e}")
        
        return GenerateSMSLinkResponse(
            success=True,
            sms_link=result['short_url'],  # Changed from 'sms_link' to 'short_url'
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
    1. Store completion/failure record in database
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
        
        # Record filing attempt in database
        filing_data = {
            'phone': request.phone,
            'gstin': request.gstin,
            'gst_type': request.gst_type,
            'period': request.period,
            'status': request.status,
            'timestamp': datetime.now()
        }
        
        # Update filing attempt status
        await filing_service.update_filing_status(
            phone=request.phone,
            gstin=request.gstin,
            period=request.period,
            gst_type=request.gst_type,
            status=request.status
        )
        
        # Store in filings collection (immutable log)
        db = await get_database()
        await db.filings.insert_one(filing_data)
        
        # Update user record (create if doesn't exist)
        await user_service.update_or_create_user(
            user_id=request.phone,
            gstin=request.gstin,
            last_filing_status=request.status
        )
        
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
            "track-completion": "POST /api/v1/track-completion",
            "analytics": "GET /api/v1/analytics"
        }
    }


# ============================================================================
# Admin Analytics Endpoint (Optional - for monitoring)
# ============================================================================

@router.get("/analytics", tags=["Admin"])
async def get_analytics() -> Dict[str, Any]:
    \"\"\"
    Get platform analytics for admin dashboard.
    
    **Note:** In production, protect this endpoint with authentication.
    
    Returns:
        Comprehensive analytics including:
        - Total users (registered, verified)
        - Filing statistics (initiated, completed, failed)
        - Completion rates
        - Filing type breakdown (3B, R1, C8)
        - Monthly trends
    \"\"\"
    try:
        analytics = await filing_service.get_platform_analytics()
        return {
            "success": True,
            "data": analytics,
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.exception(f"Error generating analytics: {str(e)}\")
        return {
            "success": False,
            "error": "Failed to generate analytics"
        }


# ============================================================================
# Admin Analytics Endpoint (Optional - for monitoring)
# ============================================================================

@router.get("/analytics", tags=["Admin\"])
async def get_analytics() -> Dict[str, Any]:
    \"\"\"
    Get platform analytics for admin dashboard.
    
    **Note:** In production, protect this endpoint with authentication.
    
    Returns:
        Comprehensive analytics including:
        - Total users (registered, verified)
        - Filing statistics (initiated, completed, failed)
        - Completion rates
        - Filing type breakdown (3B, R1, C8)
        - Monthly trends
    \"\"\"
    try:
        analytics = await filing_service.get_platform_analytics()
        return {
            "success": True,
            "data": analytics,
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.exception(f"Error generating analytics: {str(e)}\")
        return {
            "success": False,
            "error": "Failed to generate analytics"
        }
