from fastapi import APIRouter, HTTPException
from ..auth.password import (
    hash_password,
    validate_password_strength,
    is_password_common
)
from ..models.user import UserCreate

router = APIRouter()

@router.post("/register")
async def register(request: UserCreate):
    password = request.password

    # 1️⃣ Validate password strength
    is_valid, msg = validate_password_strength(password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=msg)

    # 2️⃣ Prevent common passwords
    if is_password_common(password):
        raise HTTPException(status_code=400, detail="Password is too common")

    # 3️⃣ Hash password
    try:
        password_hash = hash_password(password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 4️⃣ Save user to DB (pseudo-code)
    # user = create_user(username=request.username, password_hash=password_hash)

    return {"message": "User registered successfully"}