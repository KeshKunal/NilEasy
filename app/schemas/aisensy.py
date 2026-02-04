"""
app/schemas/aisensy.py

Pydantic models for AiSensy API request/response validation.
These schemas ensure type safety and automatic validation for all API endpoints.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
import re


class ValidateGSTINRequest(BaseModel):
    """Request schema for GSTIN validation endpoint."""
    
    gstin: str = Field(
        ..., 
        min_length=15, 
        max_length=15,
        description="15-character GSTIN"
    )
    
    @field_validator('gstin')
    @classmethod
    def validate_gstin_format(cls, v: str) -> str:
        """Validate GSTIN format."""
        v = v.strip().upper()
        if not re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', v):
            raise ValueError('Invalid GSTIN format')
        return v


class ValidateGSTINResponse(BaseModel):
    """Response schema for GSTIN validation endpoint."""
    
    valid: bool = Field(..., description="Whether GSTIN format is valid")
    captcha_url: Optional[str] = Field(default=None, description="URL to fetch captcha image")
    session_id: Optional[str] = Field(default=None, description="Session ID for captcha verification")
    error: Optional[str] = Field(default=None, description="Error message if validation failed")


class VerifyCaptchaRequest(BaseModel):
    """Request schema for captcha verification endpoint."""
    
    session_id: str = Field(..., description="Session ID from captcha fetch")
    gstin: str = Field(..., min_length=15, max_length=15, description="GSTIN to verify")
    captcha: str = Field(..., min_length=3, description="Captcha text entered by user")
    
    @field_validator('gstin', 'captcha')
    @classmethod
    def clean_input(cls, v: str) -> str:
        """Clean and uppercase input."""
        return v.strip().upper()


class BusinessDetails(BaseModel):
    """Business details from GST portal."""
    
    business_name: str = Field(..., description="Trade/Business name")
    legal_name: str = Field(..., description="Legal registered name")
    address: str = Field(..., description="Principal place of business address")
    registration_date: str = Field(..., description="GST registration date")
    status: str = Field(..., description="Active/Inactive status")
    gstin: str = Field(..., description="GSTIN")


class VerifyCaptchaResponse(BaseModel):
    """Response schema for captcha verification endpoint."""
    
    success: bool = Field(..., description="Whether verification succeeded")
    business_details: Optional[BusinessDetails] = Field(default=None, description="Business details if successful")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class GenerateSMSLinkRequest(BaseModel):
    """Request schema for SMS link generation endpoint."""
    
    gstin: str = Field(..., min_length=15, max_length=15, description="GSTIN")
    gst_type: str = Field(..., description="GST return type: '3B' or 'R1'")
    period: str = Field(..., min_length=6, max_length=6, description="Period in MMYYYY format")
    
    @field_validator('gst_type')
    @classmethod
    def validate_gst_type(cls, v: str) -> str:
        """Validate GST type."""
        v = v.strip().upper()
        if v not in ['3B', 'R1']:
            raise ValueError("GST type must be '3B' or 'R1'")
        return v
    
    @field_validator('period')
    @classmethod
    def validate_period(cls, v: str) -> str:
        """Validate period format (MMYYYY)."""
        v = v.strip()
        if not re.match(r'^(0[1-9]|1[0-2])(19|20)\d{2}$', v):
            raise ValueError("Period must be in MMYYYY format (e.g., 022025)")
        return v


class GenerateSMSLinkResponse(BaseModel):
    """Response schema for SMS link generation endpoint."""
    
    success: bool = Field(..., description="Whether link generation succeeded")
    sms_link: Optional[str] = Field(default=None, description="Clickable SMS deep link")
    sms_preview: Optional[str] = Field(default=None, description="Preview of SMS text")
    instruction: Optional[str] = Field(default=None, description="Instructions for user")
    warning: Optional[str] = Field(default=None, description="Warning message")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class TrackCompletionRequest(BaseModel):
    """Request schema for completion tracking endpoint."""
    
    phone: str = Field(..., description="User's phone number")
    gstin: str = Field(..., min_length=15, max_length=15, description="GSTIN")
    gst_type: str = Field(..., description="GST return type")
    period: str = Field(..., min_length=6, max_length=6, description="Period in MMYYYY")
    status: str = Field(..., description="Filing status: 'completed' or 'failed'")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status."""
        v = v.strip().lower()
        if v not in ['completed', 'failed']:
            raise ValueError("Status must be 'completed' or 'failed'")
        return v


class TrackCompletionResponse(BaseModel):
    """Response schema for completion tracking endpoint."""
    
    tracked: bool = Field(..., description="Whether tracking succeeded")
    message: Optional[str] = Field(default=None, description="Success message")
    error: Optional[str] = Field(default=None, description="Error message if failed")
