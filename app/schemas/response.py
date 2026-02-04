from pydantic import BaseModel
from typing import Optional, Any

class ErrorResponse(BaseModel):
    """
    Standard error response structure.
    """
    error: str
    code: str
    details: Optional[Any] = None
