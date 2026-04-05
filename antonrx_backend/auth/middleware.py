"""
Authentication & Security Middleware
FastAPI dependencies for protecting routes and securing endpoints
"""

import logging
import time
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .jwt_handler import verify_token, verify_refresh_token, is_token_expired
from ..utils.error_handler import ErrorHandler, AuthenticationError, AuthorizationError
from ..utils.rate_limiter import check_rate_limit
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# HTTP Bearer scheme for JWT in Authorization header
bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    """Current authenticated user extracted from JWT token."""
    
    def __init__(self, user_id: str, email: str, role: str = "user"):
        self.user_id = user_id
        self.email = email
        self.role = role


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> CurrentUser:
    """Dependency to extract and verify JWT from Authorization header."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        token_data = verify_token(credentials.credentials)
        return CurrentUser(
            user_id=token_data.get("user_id"),
            email=token_data.get("email"),
            role=token_data.get("role", "user")
        )
    except Exception as e:
        logger.warning(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_admin(
    current_user: CurrentUser = Depends(get_current_user)
) -> CurrentUser:
    """Dependency to ensure current user has admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def require_admin(
    current_user: CurrentUser = Depends(get_current_user)
) -> CurrentUser:
    """Ensure user is an admin."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for this operation"
        )
    return current_user
