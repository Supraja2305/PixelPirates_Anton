# api/auth_route.py
# ============================================================
# Authentication endpoints:
#   POST /api/auth/register  ← Create a new user
#   POST /api/auth/login     ← Get a JWT token
#   GET  /api/auth/me        ← Get current user info
# ============================================================

import uuid
from fastapi import APIRouter, Depends, HTTPException, status

from ..models.user import UserCreate, UserInDB, UserPublic, TokenRequest, Token, TokenData
from ..auth.password import hash_password, verify_password
from ..auth.jwt_handler import create_access_token
from ..auth.middleware import get_current_user
from ..storage.firestore_client import save_user, get_user_by_email, get_user_by_id

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=UserPublic, status_code=201)
async def register(user_data: UserCreate):
    """
    Register a new user.

    Steps:
    1. Check if email is already taken.
    2. Hash the password (never store plain text!).
    3. Generate a unique user_id.
    4. Save to Firestore.
    5. Return the public user object (no password).
    """
    # Check for existing user with same email
    existing = get_user_by_email(user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists"
        )

    # Hash password
    hashed_pw = hash_password(user_data.password)

    # Create user record
    user_id = str(uuid.uuid4())
    user_in_db = UserInDB(
        user_id=user_id,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_pw,
        role=user_data.role,
    )

    save_user(user_in_db.model_dump(mode="json"))

    return UserPublic(
        user_id=user_id,
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=True,
    )


@router.post("/login", response_model=Token)
async def login(credentials: TokenRequest):
    """
    Authenticate a user and return a JWT access token.

    Steps:
    1. Look up user by email.
    2. Verify password against stored hash.
    3. Check user is active.
    4. Create and return JWT token.

    The returned token must be included in all protected requests:
      Authorization: Bearer <token>
    """
    # Look up user
    user_dict = get_user_by_email(credentials.email)
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Verify password
    if not verify_password(credentials.password, user_dict.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check account is active
    if not user_dict.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    # Generate token
    from models.user import UserRole
    role = UserRole(user_dict.get("role", "user"))
    token = create_access_token(user_id=user_dict["user_id"], role=role)

    return Token(access_token=token, token_type="bearer")


@router.get("/me", response_model=UserPublic)
async def get_me(current_user: TokenData = Depends(get_current_user)):
    """
    Return the currently authenticated user's profile.
    Requires a valid JWT in the Authorization header.
    """
    user_dict = get_user_by_id(current_user.user_id)
    if not user_dict:
        raise HTTPException(status_code=404, detail="User not found")

    return UserPublic(
        user_id=user_dict["user_id"],
        email=user_dict["email"],
        full_name=user_dict["full_name"],
        role=user_dict["role"],
        is_active=user_dict.get("is_active", True),
    )