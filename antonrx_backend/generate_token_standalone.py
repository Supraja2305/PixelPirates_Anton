#!/usr/bin/env python3
"""
Standalone JWT Token Generator for AntonRX Backend Testing
This script avoids relative imports by importing modules directly.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv('.env')

# Import required libraries
from jose import jwt
from pydantic import BaseModel

# Define the models locally to avoid import issues
class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

class TokenData(BaseModel):
    user_id: Optional[str] = None
    role: Optional[UserRole] = None

# Define settings locally
class Settings:
    def __init__(self):
        self.secret_key = os.getenv("SECRET_KEY", "your-secret-key-here")
        self.algorithm = os.getenv("ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

def create_access_token(user_id: str, role: UserRole) -> str:
    """Create a JWT access token."""
    settings = Settings()

    # Calculate expiration time
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)

    # Create token data
    to_encode = {
        "sub": user_id,
        "role": role.value,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    # Encode the JWT
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def main():
    # Generate a JWT token for testing
    user_id = "test-user-123"
    role = UserRole.ADMIN  # Give admin access for testing

    token = create_access_token(user_id, role)

    print("JWT Token Generated for Testing:")
    print("=" * 60)
    print(token)
    print("=" * 60)
    print()
    print("Use this token in your API requests:")
    print("Authorization: Bearer " + token)
    print()
    print("Example curl command:")
    print(f'curl -H "Authorization: Bearer {token}" http://localhost:8000/api/some-protected-endpoint')
    print()
    print("Example Python requests:")
    print(f'''import requests
headers = {{"Authorization": "Bearer {token}"}}
response = requests.get("http://localhost:8000/api/some-protected-endpoint", headers=headers)
print(response.json())
''')

if __name__ == "__main__":
    main()