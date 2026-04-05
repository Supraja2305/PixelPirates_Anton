#!/usr/bin/env python3
"""
JWT Token Generator for AntonRX Backend Testing
Run this from the antonrx_backend directory
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Load environment variables
from dotenv import load_dotenv
load_dotenv('.env')

# Import our modules
from auth.jwt_handler import create_access_token
from models.user import UserRole

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