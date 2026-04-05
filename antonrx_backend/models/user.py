"""
User and Authentication Models
Pydantic models for user accounts, authentication, and JWT tokens
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


class UserRole(str, Enum):
    """User roles in the system."""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class TokenData(BaseModel):
    """Data stored in JWT token."""
    user_id: str
    email: str
    role: str = UserRole.USER.value


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class TokenRequest(BaseModel):
    """Request to create a token (deprecated - use login instead)."""
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=12)
    full_name: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!@#",
                "full_name": "John Doe"
            }
        }


class UserPublic(BaseModel):
    """User info returned by API (no password)."""
    user_id: str
    email: EmailStr
    full_name: Optional[str] = None
    role: str = UserRole.USER.value
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "uuid-here",
                "email": "user@example.com",
                "full_name": "John Doe",
                "role": "user",
                "created_at": "2024-01-01T00:00:00"
            }
        }


class UserInDB(UserPublic):
    """User record as stored in database (includes password hash)."""
    password_hash: str
