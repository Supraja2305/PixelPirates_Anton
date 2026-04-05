"""
JWT Authentication Handler for AntonRX Backend
Handles token creation, verification, and validation with OpenAI integration
"""

from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from ..config import get_settings
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


def create_access_token(
    user_id: str,
    email: str,
    role: str = "user",
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: User ID from Supabase
        email: User email address
        role: User role ('admin' or 'user')
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT token string
    """
    to_encode = {
        "sub": user_id,
        "email": email,
        "role": role,
        "token_type": "access",
        "iat": datetime.now(timezone.utc)
    }
    
    # Set expiration time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    
    to_encode["exp"] = expire
    
    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.algorithm
        )
        logger.info(f"Access token created for user: {email}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create token"
        )


def create_refresh_token(user_id: str, email: str) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        user_id: User ID from Supabase
        email: User email address
    
    Returns:
        Encoded refresh token string
    """
    to_encode = {
        "sub": user_id,
        "email": email,
        "token_type": "refresh",
        "iat": datetime.now(timezone.utc)
    }
    
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    to_encode["exp"] = expire
    
    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.algorithm
        )
        logger.info(f"Refresh token created for user: {email}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating refresh token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create refresh token"
        )


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT access token.
    
    Args:
        token: JWT token to verify
    
    Returns:
        Decoded token payload with user_id, email, role, etc.
    
    Raises:
        HTTPException: If token is invalid, expired, or tampered
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        
        # Verify token type
        token_type = payload.get("token_type")
        if token_type != "access":
            logger.warning("Token type mismatch in verification")
            raise credentials_exception
        
        # Extract required claims
        user_id: Optional[str] = payload.get("sub")
        email: Optional[str] = payload.get("email")
        role: str = payload.get("role", "user")
        
        if not user_id or not email:
            logger.warning("Missing required claims in token")
            raise credentials_exception
        
        return {
            "user_id": user_id,
            "email": email,
            "role": role,
            "token_type": token_type,
            "exp": payload.get("exp")
        }
        
    except JWTError as e:
        logger.error(f"JWT validation error: {str(e)}")
        raise credentials_exception


def verify_refresh_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a refresh token.
    
    Args:
        token: Refresh token to verify
    
    Returns:
        Decoded token payload
    
    Raises:
        HTTPException: If token is invalid or not a refresh token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        
        # Verify token type
        token_type = payload.get("token_type")
        if token_type != "refresh":
            logger.warning("Token type is not refresh")
            raise credentials_exception
        
        user_id: Optional[str] = payload.get("sub")
        email: Optional[str] = payload.get("email")
        
        if not user_id or not email:
            logger.warning("Missing required claims in refresh token")
            raise credentials_exception
        
        return {
            "user_id": user_id,
            "email": email,
            "token_type": token_type
        }
        
    except JWTError as e:
        logger.error(f"Refresh token validation error: {str(e)}")
        raise credentials_exception


def decode_token_safely(token: str) -> Optional[Dict[str, Any]]:
    """
    Safely decode token without raising exceptions.
    Used for optional authentication checks.
    
    Args:
        token: JWT token to decode
    
    Returns:
        Decoded payload or None if invalid/expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        return None


def is_token_expired(token: str) -> bool:
    """
    Check if a token has expired without raising exceptions.
    
    Args:
        token: JWT token to check
    
    Returns:
        True if token is expired, False otherwise
    """
    payload = decode_token_safely(token)
    if not payload:
        return True
    
    exp = payload.get("exp")
    if not exp:
        return True
    
    try:
        expiration = datetime.fromtimestamp(exp, tz=timezone.utc)
        return expiration <= datetime.now(timezone.utc)
    except Exception:
        return True
