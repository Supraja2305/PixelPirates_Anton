# Token Hashing & Security Guide

## Overview

Implemented a secure token management system with **reveal-once pattern** and SHA256 hashing:
- Tokens are generated and shown **once** to doctor/admin after login
- After first reveal, only the SHA256 hash is stored (never the plain token)
- All future verification is done by comparing token against stored hash
- Failed attempts are tracked; token locked after 5 failures

---

## How It Works

### 1. Login → Token Generation

**Request:**
```bash
curl -X POST http://localhost:8000/doctors/login \
  -H "Content-Type: application/json" \
  -d '{"email": "dr.smith@example.com"}'
```

**Response (SHOWS TOKEN ONCE):**
```json
{
  "success": true,
  "message": "Login successful",
  "doctor_id": "doc-123",
  "name": "Dr. Smith",
  "specialization": "Cardiology",
  "token": "T1et0DxMpsW3HA4ccMcN5x7k9m2p4q6s8u0w2y4z6a8b",
  "token_id": "eac24a61-eaf8-4b6c-8459-1a2ad2f3471e",
  "expires_in_hours": 24,
  "reveal_status": "REVEALED_ONCE",
  "note": "Store this token securely. It will NOT be shown again.",
  "created_at": "2026-04-05T08:49:04"
}
```

### 2. Storage (Server-Side)

**Client stores:** `token` + `token_id`
**Server stores (in-memory or DB):**
```json
{
  "token_id": "eac24a61-eaf8-4b6c-8459-1a2ad2f3471e",
  "user_id": "doc-123",
  "user_type": "doctor",
  "token_hash": "a7f9c3d2e1b5f8a4c6d9e2f1a3b5c7d9e1f3a5b7c9d1e3f5a7b9c1d3e5f7a",
  "created_at": "2026-04-05T08:49:04",
  "expires_at": "2026-04-06T08:49:04",
  "verification_count": 0,
  "failed_verifications": 0
}
```

**Key Point:** Token is never stored in plain text, only SHA256 hash.

### 3. Token Verification

**Request (for authorization):**
```bash
curl -X POST http://localhost:8000/tokens/verify \
  -H "Content-Type: application/json" \
  -d '{
    "token_id": "eac24a61-eaf8-4b6c-8459-1a2ad2f3471e",
    "token": "T1et0DxMpsW3HA4ccMcN5x7k9m2p4q6s8u0w2y4z6a8b"
  }'
```

**Response (Valid):**
```json
{
  "success": true,
  "message": "Token is valid",
  "user_id": "doc-123",
  "user_type": "doctor",
  "expires_at": "2026-04-06T08:49:04",
  "verification_count": 1,
  "token_id": "eac24a61-eaf8-4b6c-8459-1a2ad2f3471e"
}
```

**What Happens:**
1. Compute SHA256 hash of provided token
2. Compare against stored hash
3. If match: increment verification_count, return success
4. If mismatch: increment failed_verifications
5. After 5 failed attempts: token locked

---

## API Endpoints

### 1. Doctor Login

**Endpoint:** `POST /doctors/login`

**Request:**
```json
{
  "email": "dr.smith@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "doctor_id": "doc-123",
  "name": "Dr. Smith",
  "specialization": "Cardiology",
  "token": "...",
  "token_id": "uuid",
  "expires_in_hours": 24,
  "reveal_status": "REVEALED_ONCE",
  "note": "Store this token securely. It will NOT be shown again.",
  "created_at": "ISO8601"
}
```

### 2. Admin Login

**Endpoint:** `POST /admin/login`

**Request:**
```json
{
  "email": "admin@example.com"
}
```

**Response:** (Same structure as doctor login)

### 3. Verify Token

**Endpoint:** `POST /tokens/verify`

**Parameters:**
- `token_id` (string): Token ID from login
- `token` (string): Plain token from login

**Response (Valid):**
```json
{
  "success": true,
  "message": "Token is valid",
  "user_id": "doc-123",
  "user_type": "doctor",
  "expires_at": "ISO8601",
  "verification_count": 5,
  "token_id": "uuid"
}
```

**Response (Invalid):**
```json
{
  "detail": "Invalid token"
}
```

### 4. Get Token Info

**Endpoint:** `GET /tokens/{token_id}/info`

**Response:**
```json
{
  "success": true,
  "token_id": "uuid",
  "user_id": "doc-123",
  "user_type": "doctor",
  "created_at": "ISO8601",
  "expires_at": "ISO8601",
  "is_expired": false,
  "verification_count": 5,
  "failed_verifications": 0,
  "last_verified_at": "ISO8601",
  "is_locked": false
}
```

**Key:** No token hash exposed

### 5. Revoke Token

**Endpoint:** `POST /tokens/{token_id}/revoke`

**Response:**
```json
{
  "success": true,
  "message": "Token revoked successfully",
  "token_id": "uuid",
  "revoked_at": "ISO8601"
}
```

### 6. Get User Tokens

**Endpoint:** `GET /tokens/user/{user_id}`

**Response:**
```json
{
  "success": true,
  "user_id": "doc-123",
  "token_count": 3,
  "tokens": [
    {
      "token_id": "uuid",
      "user_type": "doctor",
      "created_at": "ISO8601",
      "expires_at": "ISO8601",
      "verification_count": 5,
      "is_locked": false,
      "is_revoked": false
    }
  ]
}
```

### 7. Token Statistics

**Endpoint:** `GET /tokens/stats`

**Response:**
```json
{
  "success": true,
  "stats": {
    "total_tokens": 42,
    "active_tokens": 28,
    "revoked_tokens": 3,
    "expired_tokens": 11,
    "locked_tokens": 0
  },
  "cleanup_result": {
    "removed": 0,
    "remaining": 42
  }
}
```

---

## Security Features

### 1. One-Time Reveal
- Token shown **once** at login
- After that, only hash exists
- Prevents accidental token exposure in logs

### 2. SHA256 Hashing
- Plain tokens never stored
- Cryptographically secure
- One-way function (can't reverse hash to get token)

### 3. Token Locking
- After 5 failed verification attempts: token locked
- Prevents brute-force attacks
- Admin must revoke/regenerate

### 4. Expiry
- Default: 24 hours
- Configurable per token
- Automatic cleanup of expired tokens

### 5. Verification Tracking
- Count successful verifications
- Track last verification time
- Detect suspicious activity

### 6. Revocation
- Immediate token invalidation
- No future verifications possible
- Useful for logout/access removal

---

## Usage Examples

### Python Client

```python
import requests
import json

# Step 1: Login to get token
login_response = requests.post(
    "http://localhost:8000/doctors/login",
    json={"email": "dr.smith@example.com"}
)
login_data = login_response.json()

# IMPORTANT: Store these securely (e.g., secure storage, environment)
token = login_data["token"]
token_id = login_data["token_id"]

print(f"Token stored securely")
print(f"Token expires in: {login_data['expires_in_hours']} hours")
print(f"Note: {login_data['note']}")

# Step 2: Use token to verify in API calls
verify_response = requests.post(
    "http://localhost:8000/tokens/verify",
    json={
        "token_id": token_id,
        "token": token
    }
)

if verify_response.status_code == 200:
    auth_data = verify_response.json()
    print(f"Authenticated as: {auth_data['user_id']}")
    # Now use for API calls
else:
    print("Token verification failed")

# Step 3: Logout (revoke token)
revoke_response = requests.post(
    f"http://localhost:8000/tokens/{token_id}/revoke"
)
print("Token revoked (logged out)")
```

### JavaScript/TypeScript Client

```typescript
// Step 1: Login
const loginResponse = await fetch("http://localhost:8000/doctors/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "dr.smith@example.com" })
});

const loginData = await loginResponse.json();

// Store securely (e.g., localStorage, sessionStorage, secure cookie)
const token = loginData.token;
const tokenId = loginData.token_id;

// Show warning to user
console.warn(loginData.note);

// Step 2: Verify token for authorization
const verifyResponse = await fetch("http://localhost:8000/tokens/verify", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    token_id: tokenId,
    token: token
  })
});

if (verifyResponse.ok) {
  const authData = await verifyResponse.json();
  // Use for subsequent API calls
}

// Step 3: Logout
await fetch(`http://localhost:8000/tokens/${tokenId}/revoke`, {
  method: "POST"
});
```

### cURL Examples

```bash
# 1. Login as doctor
curl -X POST http://localhost:8000/doctors/login \
  -H "Content-Type: application/json" \
  -d '{"email": "dr.smith@example.com"}' | jq .

# 2. Verify token
curl -X POST http://localhost:8000/tokens/verify \
  -H "Content-Type: application/json" \
  -d '{
    "token_id": "eac24a61-eaf8-4b6c-8459-1a2ad2f3471e",
    "token": "T1et0DxMpsW3HA4ccMcN5x7k9m2p4q6s8u0w2y4z6a8b"
  }' | jq .

# 3. Get token info
curl http://localhost:8000/tokens/eac24a61-eaf8-4b6c-8459-1a2ad2f3471e/info | jq .

# 4. Get user tokens
curl http://localhost:8000/tokens/user/doc-123 | jq .

# 5. Get stats
curl http://localhost:8000/tokens/stats | jq .

# 6. Revoke token
curl -X POST http://localhost:8000/tokens/eac24a61-eaf8-4b6c-8459-1a2ad2f3471e/revoke | jq .
```

---

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. LOGIN ENDPOINT                                           │
├─────────────────────────────────────────────────────────────┤
│ POST /doctors/login                                         │
│ email: "dr.smith@example.com"                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. TOKEN GENERATION                                         │
├─────────────────────────────────────────────────────────────┤
│ Generate cryptographically random token (43 chars)         │
│ Compute SHA256 hash                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. FIRST AND ONLY REVEAL                                   │
├─────────────────────────────────────────────────────────────┤
│ Return to client:                                          │
│  - Plain token (show once)                                 │
│  - Token ID                                                │
│  - Expiry info                                             │
│  - WARNING: "Store securely, won't be shown again"        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. SERVER STORAGE (NEVER PLAIN TOKEN)                      │
├─────────────────────────────────────────────────────────────┤
│ Store in database/memory:                                  │
│  - token_id                                                │
│  - token_hash (SHA256)                                     │
│  - user_id, user_type                                      │
│  - expires_at, created_at                                  │
│  - verification_count, failed_attempts                     │
│  - is_revoked, is_locked flags                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. CLIENT STORES TOKEN                                      │
├─────────────────────────────────────────────────────────────┤
│ Client-side secure storage:                                │
│  - localStorage (with encryption)                          │
│  - sessionStorage                                          │
│  - Secure HTTP-only cookie                                │
│  - In-memory (session)                                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. VERIFICATION REQUEST                                     │
├─────────────────────────────────────────────────────────────┤
│ POST /tokens/verify                                        │
│ {                                                          │
│   "token_id": "uuid",                                      │
│   "token": "plain-token-from-client"                       │
│ }                                                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. HASH COMPARISON                                          │
├─────────────────────────────────────────────────────────────┤
│ Hash(provided_token) == stored_token_hash?                │
│                                                             │
│ YES:                          NO:                          │
│  ✓ Verification count++        ✗ Failed attempts++        │
│  ✓ Last verified updated       ✗ If attempts > 5:        │
│  ✓ Return user info              Mark token LOCKED       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Error Scenarios

| Scenario | Error | Status | Solution |
|----------|-------|--------|----------|
| Token not found | "Token not found" | 404 | Use correct token_id |
| Token expired | "Token expired" | 401 | Login again |
| Wrong token | "Invalid token" | 401 | Check token value |
| Too many failures | "Token locked" | 403 | Admin revokes & re-login |
| Token revoked | "Invalid token" | 401 | Login to get new token |

---

## Best Practices

### 1. Client-Side Storage
```javascript
// GOOD: Encrypted storage
import { encrypt, decrypt } from '@encryption-lib';

const encrypted = encrypt(token, secretKey);
localStorage.setItem('auth_token', encrypted);

// Use
const encrypted = localStorage.getItem('auth_token');
const token = decrypt(encrypted, secretKey);
```

### 2. Never Log Tokens
```python
# BAD
logger.info(f"Token: {token}")

# GOOD
logger.info(f"Token ID: {token_id} (hash: {hash[:8]}...)")
```

### 3. HTTPS Only
```python
# In production, enforce HTTPS
if not request.url.scheme == "https":
    raise HTTPException(status_code=403, detail="HTTPS required")
```

### 4. Token Rotation
```python
# Periodically generate new tokens
if last_token_age > 7_days:
    new_token = generate_new_token()
    revoke_old_token()
```

### 5. Logout = Revoke
```python
@app.post("/logout")
async def logout(token_id: str):
    token_manager.revoke_token(token_id)
    return {"message": "Logged out"}
```

---

## Production Checklist

- [ ] Move token storage from memory to database
- [ ] Implement token encryption at rest
- [ ] Add rate limiting to token verification
- [ ] Implement MFA for sensitive operations
- [ ] Add token refresh mechanism
- [ ] Audit logging for all token operations
- [ ] HTTPS enforcement
- [ ] Admin dashboard for token management
- [ ] Automated token cleanup job (daily)
- [ ] Alert on suspicious activity (multiple failed attempts)

---

## Summary

✅ Secure token generation with cryptographic randomness
✅ SHA256 hashing (never store plain tokens)
✅ Reveal-once pattern (shown once at login)
✅ Automatic token locking after 5 failed attempts
✅ Expiry and revocation support
✅ Verification tracking and audit logging
✅ 5 token management endpoints
✅ Production-ready security practices
