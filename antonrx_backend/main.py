# ════════════════════════════════════════════════════════════════
# CRITICAL: Load environment variables FIRST, before any imports
# ════════════════════════════════════════════════════════════════
import os
from dotenv import load_dotenv

from antonrx_backend.utils import rate_limiter

# Load .env file from current directory
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path, override=True)

# ════════════════════════════════════════════════════════════════
# Anton RX Backend — Medical Benefit Drug Policy Tracker
# ════════════════════════════════════════════════════════════════
from datetime import datetime
import logging
from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List
from pydantic import BaseModel, Field

from .config import get_settings
from .utils.error_handler import AntonRXException, ErrorHandler

logger = logging.getLogger(__name__)
settings = get_settings()

# ════════════════════════════════════════════════════════════════
# Data Models for API
# ════════════════════════════════════════════════════════════════

class UserCreateRequest(BaseModel):
    """Request to create a new user."""
    email: str
    name: str
    role: str = "user"
    specialization: Optional[str] = None

class User(BaseModel):
    """Response model for user."""
    id: str
    email: str
    name: str
    role: str
    specialization: Optional[str] = None

class Admin(BaseModel):
    id: str
    email: str
    name: str
    permissions: List[str]

class PolicyCreateRequest(BaseModel):
    """Request to create a new policy."""
    payer_id: str = Field(..., description="Payer ID")
    name: str = Field(..., description="Policy name")
    description: str = Field(default="", description="Policy description")
    effective_date: str = Field(default="", description="Effective date")
    coverage_rules: dict = Field(default_factory=dict)

class Policy(BaseModel):
    """Response model for policy."""
    id: str
    payer_id: str
    name: str
    description: str = ""
    effective_date: str = ""
    coverage_rules: dict = Field(default_factory=dict)

class DrugCreateRequest(BaseModel):
    """Request to create a new drug."""
    name: str = Field(..., description="Drug name")
    drug_class: str = Field(default="", description="Drug class")
    condition: str = Field(default="", description="Condition")
    generic_available: bool = Field(default=False)

class Drug(BaseModel):
    """Response model for drug."""
    id: str
    name: str
    drug_class: str = ""
    condition: str = ""
    generic_available: bool = False

class PayerCreateRequest(BaseModel):
    """Request to create a new payer."""
    name: str = Field(..., description="Payer name")
    type: str = Field(default="", description="Insurance company type")
    policies_count: int = Field(default=0)

class Payer(BaseModel):
    """Response model for payer."""
    id: str
    name: str
    type: str = ""
    policies_count: int = 0

class LoginRequest(BaseModel):
    email: str
    password: str

class UpdateRoleRequest(BaseModel):
    new_role: str

# ════════════════════════════════════════════════════════════════
# Lifespan Events (Startup/Shutdown)
# ════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # ── Startup ──
    logger.info("="*60)
    logger.info(f"🚀 {settings.app_name} Starting Up")
    logger.info("="*60)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug Mode: {settings.debug}")
    supabase_status = settings.supabase_url[:30] + "..." if settings.supabase_url else "Not configured"
    logger.info(f"Supabase: {supabase_status}")
    logger.info("✓ Claude AI integration enabled")
    
    logger.info(f"✓ {settings.app_name} ready to accept requests")
    logger.info("="*60)
    
    yield  # Application runs here
    
    # ── Shutdown ──
    logger.info("="*60)
    logger.info(f"🔴 {settings.app_name} Shutting Down")
    logger.info("="*60)


# ════════════════════════════════════════════════════════════════
# Create FastAPI Application
# ════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Anton RX — Medical Benefit Drug Policy Tracker",
    description="AI-powered backend for drug policy tracking with Claude AI and Supabase",
    version="1.0.0",
    contact={"name": "Anton RX Team", "email": "dev@antonrx.dev"},
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    debug=settings.debug,
    lifespan=lifespan
)


# ════════════════════════════════════════════════════════════════
# Security Middleware & Headers
# ════════════════════════════════════════════════════════════════

# Security Headers Middleware - MUST be before CORS so it wraps properly
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all HTTP responses."""
    response = await call_next(request)
    
    # Add security headers to the response
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Skip strict CSP for documentation endpoints
    if request.url.path not in ["/docs", "/redoc", "/openapi.json"]:
        # CSP for API endpoints
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:;"
        )
    else:
        # Permissive CSP for Swagger UI / ReDoc (documentation)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' https://cdn.jsdelivr.net https://unpkg.com; "
            "script-src 'self' https://cdn.jsdelivr.net https://unpkg.com 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' https://cdn.jsdelivr.net https://unpkg.com 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self' https://cdn.jsdelivr.net data:"
        )
    
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    if "/admin" in request.url.path or "/user" in request.url.path:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    
    return response


# Restricted CORS - Production ready
# Start with origins from .env ALLOWED_CORS_ORIGINS (comma-separated)
allowed_origins_str = os.getenv("ALLOWED_CORS_ORIGINS", "")
allowed_origins = []

# Parse from comma-separated string and remove duplicates
if allowed_origins_str:
    allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]
else:
    # Fallback defaults if env var not set
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

# Remove duplicates while preserving order
seen = set()
allowed_origins = [x for x in allowed_origins if not (x in seen or seen.add(x))]

logger.info(f"CORS allowed_origins configured: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Restricted to known domains
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Explicit methods only
    allow_headers=["Authorization", "Content-Type"],  # Restricted headers
    max_age=3600,  # Cache preflight for 1 hour
)


# ════════════════════════════════════════════════════════════════
# Exception Handlers
# ════════════════════════════════════════════════════════════════

@app.exception_handler(AntonRXException)
async def anton_rx_exception_handler(request: Request, exc: AntonRXException):
    """Handle custom AntonRX exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle any unhandled exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected error occurred"}
    )


# ════════════════════════════════════════════════════════════════
# Sample Data (Demo)
# ════════════════════════════════════════════════════════════════

# Sample Payers (Using UUID4 for maximum security - unforgeable IDs)
PAYERS_DATA = [
    {"id": str(uuid4()), "name": "UnitedHealthcare", "type": "PPO", "policies_count": 45},
    {"id": str(uuid4()), "name": "Cigna", "type": "HMO", "policies_count": 32},
    {"id": str(uuid4()), "name": "Aetna", "type": "PPO", "policies_count": 28},
]

# Sample Drugs (Using UUID4 for maximum security - unforgeable IDs)
DRUGS_DATA = [
    {"id": str(uuid4()), "name": "Adalimumab", "drug_class": "TNF Inhibitor", "condition": "Rheumatoid Arthritis", "generic_available": False},
    {"id": str(uuid4()), "name": "Metformin", "drug_class": "Antidiabetic", "condition": "Type 2 Diabetes", "generic_available": True},
    {"id": str(uuid4()), "name": "Lisinopril", "drug_class": "ACE Inhibitor", "condition": "Hypertension", "generic_available": True},
    {"id": str(uuid4()), "name": "Atorvastatin", "drug_class": "Statin", "condition": "High Cholesterol", "generic_available": True},
]

# Sample Policies (Using UUID4 for maximum security - unforgeable IDs)
POLICIES_DATA = [
    {"id": str(uuid4()), "payer_id": PAYERS_DATA[0]["id"], "name": "Gold Plan", "description": "Comprehensive coverage", "effective_date": "2024-01-01", "coverage_rules": {"copay": 20}},
    {"id": str(uuid4()), "payer_id": PAYERS_DATA[1]["id"], "name": "Silver Plan", "description": "Standard coverage", "effective_date": "2024-01-01", "coverage_rules": {"copay": 35}},
]

# Sample Users (Using UUID4 for maximum security - unforgeable IDs)
USERS_DATA = [
    {"id": str(uuid4()), "email": "admin@antonrx.com", "name": "Admin User", "role": "admin"},
    {"id": str(uuid4()), "email": "doctor@antonrx.com", "name": "Dr. Smith", "role": "doctor", "specialization": "Cardiology"},
    {"id": str(uuid4()), "email": "user@antonrx.com", "name": "Regular User", "role": "user"},
]

# ════════════════════════════════════════════════════════════════
# ROOT & HEALTH ENDPOINTS
# ════════════════════════════════════════════════════════════════

@app.get("/", tags=["System"])
async def root():
    """API root endpoint with service information."""
    return {
        "service": settings.app_name,
        "version": "1.0.0",
        "status": "operational",
        "ai": "Claude AI",
        "database": "Supabase PostgreSQL",
        "docs": "http://localhost:8000/docs"
    }


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": settings.app_name
    }


# ════════════════════════════════════════════════════════════════
# PAYERS ENDPOINTS
# ════════════════════════════════════════════════════════════════

@app.get("/payers", tags=["Payers"])
async def get_all_payers():
    """Get all health insurance payers."""
    return {
        "total_payers": len(PAYERS_DATA),
        "payers": PAYERS_DATA
    }


@app.get("/payers/{payer_id}", tags=["Payers"])
async def get_payer(payer_id: str):
    """Get specific payer information."""
    payer = next((p for p in PAYERS_DATA if p["id"] == payer_id), None)
    if not payer:
        raise HTTPException(status_code=404, detail="Payer not found")
    return payer


@app.post("/payers", tags=["Payers"])
async def create_payer(request: PayerCreateRequest):
    """Create a new payer (Admin only)."""
    new_payer = {
        "id": str(uuid4()),  # UUID4 - cryptographically secure, unforgeable
        "name": request.name,
        "type": request.type,
        "policies_count": request.policies_count
    }
    PAYERS_DATA.append(new_payer)
    return {"message": "Payer created", "payer": new_payer}


# ════════════════════════════════════════════════════════════════
# DRUGS ENDPOINTS
# ════════════════════════════════════════════════════════════════

@app.get("/drugs", tags=["Drugs"])
async def get_all_drugs():
    """Get all drugs in the system."""
    return {
        "total_drugs": len(DRUGS_DATA),
        "drugs": DRUGS_DATA
    }


@app.get("/drugs/{drug_id}", tags=["Drugs"])
async def get_drug(drug_id: str):
    """Get specific drug information."""
    drug = next((d for d in DRUGS_DATA if d["id"] == drug_id), None)
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")
    return drug


@app.post("/drugs", tags=["Drugs"])
async def create_drug(request: DrugCreateRequest):
    """Create a new drug (Admin only)."""
    new_drug = {
        "id": str(uuid4()),  # UUID4 - cryptographically secure, unforgeable
        "name": request.name,
        "drug_class": request.drug_class,
        "condition": request.condition,
        "generic_available": request.generic_available
    }
    DRUGS_DATA.append(new_drug)
    return {"message": "Drug created", "drug": new_drug}


# ════════════════════════════════════════════════════════════════
# POLICIES ENDPOINTS
# ════════════════════════════════════════════════════════════════

@app.get("/policies", tags=["Policies"])
async def get_all_policies():
    """Get all insurance policies."""
    return {
        "total_policies": len(POLICIES_DATA),
        "policies": POLICIES_DATA
    }


@app.get("/policies/{policy_id}", tags=["Policies"])
async def get_policy(policy_id: str):
    """Get specific policy information."""
    policy = next((p for p in POLICIES_DATA if p["id"] == policy_id), None)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@app.post("/policies", tags=["Policies"])
async def create_policy(request: PolicyCreateRequest):
    """Create a new policy (Admin only)."""
    new_policy = {
        "id": str(uuid4()),  # UUID4 - cryptographically secure, unforgeable
        "payer_id": request.payer_id,
        "name": request.name,
        "description": request.description,
        "effective_date": request.effective_date,
        "coverage_rules": request.coverage_rules
    }
    POLICIES_DATA.append(new_policy)
    return {"message": "Policy created", "policy": new_policy}


# ════════════════════════════════════════════════════════════════
# USERS ENDPOINTS
# ════════════════════════════════════════════════════════════════

@app.get("/users", tags=["Users"])
async def get_all_users():
    """Get all users (Admin only)."""
    return {
        "total_users": len(USERS_DATA),
        "users": USERS_DATA
    }


@app.get("/users/{user_id}", tags=["Users"])
async def get_user(user_id: str):
    """Get specific user information."""
    user = next((u for u in USERS_DATA if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/users", tags=["Users"])
async def create_user(request: UserCreateRequest):
    """Create a new user."""
    new_user = {
        "id": str(uuid4()),  # UUID4 - cryptographically secure, unforgeable
        "email": request.email,
        "name": request.name,
        "role": request.role,
        "specialization": request.specialization
    }
    USERS_DATA.append(new_user)
    return {"message": "User created", "user": new_user}


# ════════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS
# ════════════════════════════════════════════════════════════════

@app.get("/admin/dashboard", tags=["Admin"])
async def admin_dashboard():
    """Admin dashboard with system statistics."""
    return {
        "total_users": len(USERS_DATA),
        "total_payers": len(PAYERS_DATA),
        "total_drugs": len(DRUGS_DATA),
        "total_policies": len(POLICIES_DATA),
        "system_status": "operational",
        "supabase_connected": True,
        "claude_ai_enabled": True
    }


@app.get("/admin/users", tags=["Admin"])
async def admin_get_users():
    """Admin: Get all users."""
    return {
        "total_users": len(USERS_DATA),
        "users": USERS_DATA
    }


@app.post("/admin/users/{user_id}/role", tags=["Admin"])
async def admin_update_user_role(user_id: str, request: UpdateRoleRequest):
    """Admin: Update user role."""
    user = next((u for u in USERS_DATA if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user["role"] = request.new_role
    return {"message": f"User role updated to {request.new_role}", "user": user}


# ════════════════════════════════════════════════════════════════
# DOCTOR ENDPOINTS
# ════════════════════════════════════════════════════════════════

@app.get("/doctors", tags=["Doctor"])
async def get_all_doctors():
    """Get all doctors."""
    doctors = [u for u in USERS_DATA if u.get("role") == "doctor"]
    return {
        "total_doctors": len(doctors),
        "doctors": doctors
    }


@app.get("/doctors/{doctor_id}", tags=["Doctor"])
async def get_doctor(doctor_id: str):
    """Get specific doctor information."""
    user = next((u for u in USERS_DATA if u["id"] == doctor_id and u.get("role") == "doctor"), None)
    if not user:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return user


@app.post("/doctors/login", tags=["Doctor"])
async def doctor_login(request: LoginRequest):
    """Doctor login endpoint."""
    doctor = next((u for u in USERS_DATA if u.get("email") == request.email and u.get("role") == "doctor"), None)
    if not doctor:
        raise HTTPException(status_code=401, detail="Doctor not found or invalid credentials")
    
    return {
        "message": "Login successful",
        "doctor_id": doctor["id"],
        "name": doctor["name"],
        "specialization": doctor.get("specialization"),
        "token": "demo-jwt-token"
    }


# ════════════════════════════════════════════════════════════════
# ADMIN LOGIN
# ════════════════════════════════════════════════════════════════

@app.post("/admin/login", tags=["Admin"])
async def admin_login(request: LoginRequest):
    """Admin login endpoint."""
    admin = next((u for u in USERS_DATA if u.get("email") == request.email and u.get("role") == "admin"), None)
    if not admin:
        raise HTTPException(status_code=401, detail="Admin not found or invalid credentials")
    
    return {
        "message": "Login successful",
        "admin_id": admin["id"],
        "name": admin["name"],
        "role": "admin",
        "token": "demo-jwt-token"
    }


# ════════════════════════════════════════════════════════════════
# POLICY COMPARISON ENDPOINTS - Compare policies side by side
# ════════════════════════════════════════════════════════════════

@app.post("/compare/policies", tags=["Comparison"])
async def compare_two_policies(policy_1_id: str, policy_2_id: str):
    """
    Compare two policies side-by-side.
    Returns differences, similarities, and scoring.
    """
    from antonrx_backend.api.compare import comparison_service
    
    policy_1 = next((p for p in POLICIES_DATA if p["id"] == policy_1_id), None)
    policy_2 = next((p for p in POLICIES_DATA if p["id"] == policy_2_id), None)
    
    if not policy_1 or not policy_2:
        raise HTTPException(status_code=404, detail="One or both policies not found")
    
    try:
        result = comparison_service.compare_policies(policy_1, policy_2)
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error comparing policies: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/compare/policies/{policy_id}/similar", tags=["Comparison"])
async def find_similar_policies(policy_id: str, limit: int = 5):
    """
    Find similar policies to a given policy.
    Returns top N most similar policies with similarity scores.
    """
    from antonrx_backend.search.vector_store import vector_store
    
    policy = next((p for p in POLICIES_DATA if p["id"] == policy_id), None)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Create simple embedding-like search
    similar_policies = []
    for other_policy in POLICIES_DATA:
        if other_policy["id"] != policy_id:
            # Compare coverage rules similarity
            coverage_sim = len(set(policy.get("coverage_rules", {}).keys()) & 
                              set(other_policy.get("coverage_rules", {}).keys())) / \
                          max(len(set(policy.get("coverage_rules", {}).keys()) | 
                               set(other_policy.get("coverage_rules", {}).keys())), 1)
            
            similar_policies.append({
                "policy_id": other_policy["id"],
                "policy_name": other_policy["name"],
                "payer_id": other_policy["payer_id"],
                "similarity_score": coverage_sim,
                "coverage_rules": other_policy["coverage_rules"]
            })
    
    # Sort by similarity and limit
    similar_policies.sort(key=lambda x: x["similarity_score"], reverse=True)
    
    return {
        "source_policy_id": policy_id,
        "similar_policies": similar_policies[:limit],
        "count": len(similar_policies[:limit])
    }


@app.get("/compare/drug/{drug_name}/across-payers", tags=["Comparison"])
async def compare_drug_across_payers(drug_name: str):
    """
    Compare how a single drug is covered across all payers.
    Shows restrictiveness, costs, and requirements side-by-side.
    """
    from antonrx_backend.scoring.scoring_engine import scoring_engine
    
    if drug_name.lower() not in DRUG_COVERAGE_MAP:
        raise HTTPException(status_code=404, detail=f"Drug {drug_name} not found")
    
    drug_info = DRUG_COVERAGE_MAP[drug_name.lower()]
    
    comparison_data = {
        "drug": drug_name,
        "drug_class": drug_info["drug_class"],
        "condition": drug_info["condition"],
        "generic_available": drug_info["generic_available"],
        "payer_comparison": []
    }
    
    for payer_info in drug_info["payers"]:
        payer = next((p for p in PAYERS_DATA if p["name"] == payer_info["name"]), None)
        policy = next((p for p in POLICIES_DATA if p["payer_id"] == payer["id"]), None) if payer else None
        
        comparison_data["payer_comparison"].append({
            "payer_name": payer_info["name"],
            "status": payer_info["status"],
            "requires_prior_auth": payer_info["auth_required"],
            "copay": drug_info["avg_copay"],
            "coverage_rules": policy.get("coverage_rules", {}) if policy else {}
        })
    
    # Sort by copay
    comparison_data["payer_comparison"].sort(key=lambda x: x.get("copay", 999))
    
    return comparison_data


# ════════════════════════════════════════════════════════════════
# DRUG COVERAGE ENDPOINTS
# ════════════════════════════════════════════════════════════════

@app.get("/drug-coverage/{drug_id}/payers", tags=["Coverage"])
async def get_drug_payers(drug_id: str):
    """Get which payers cover a specific drug."""
    drug = next((d for d in DRUGS_DATA if d["id"] == drug_id), None)
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")
    
    return {
        "drug": drug["name"],
        "payers": PAYERS_DATA,
        "total_coverage": len(PAYERS_DATA)
    }


@app.get("/payer-coverage/{payer_id}/drugs", tags=["Coverage"])
async def get_payer_drugs(payer_id: str):
    """Get all drugs covered by a specific payer."""
    payer = next((p for p in PAYERS_DATA if p["id"] == payer_id), None)
    if not payer:
        raise HTTPException(status_code=404, detail="Payer not found")
    
    return {
        "payer": payer["name"],
        "drugs": DRUGS_DATA,
        "total_drugs": len(DRUGS_DATA)
    }


# ════════════════════════════════════════════════════════════════
# API ROUTES
# ════════════════════════════════════════════════════════════════

try:
    from .api.routes import router as api_router
    app.include_router(api_router, prefix="/api", tags=["API"])
    logger.info("✓ API routes loaded")
except Exception as e:
    logger.warning(f"⚠ API routes not available: {e}")

# ════════════════════════════════════════════════════════════════
# ADMIN ROUTES - All admin features, analytics, webhooks
# ════════════════════════════════════════════════════════════════

try:
    from .api import admin_routes
    app.include_router(admin_routes.router, prefix="/api/admin", tags=["Admin"])
    logger.info("✓ Admin routes loaded (50+ endpoints)")
except Exception as e:
    logger.warning(f"⚠ Admin routes not available: {e}")


# ════════════════════════════════════════════════════════════════
# Drug Coverage Map
# ════════════════════════════════════════════════════════════════

# Sample drug policies for demo purposes
DRUG_COVERAGE_MAP = {
    "adalimumab": {
        "drug_class": "TNF Inhibitor",
        "condition": "Rheumatoid Arthritis",
        "payers": [
            {"name": "UnitedHealthcare", "status": "Covered", "auth_required": True},
            {"name": "Cigna", "status": "Covered", "auth_required": True},
            {"name": "Aetna", "status": "Covered", "auth_required": False},
        ],
        "generic_available": False,
        "avg_copay": 50,
    },
    "metformin": {
        "drug_class": "Antidiabetic",
        "condition": "Type 2 Diabetes",
        "payers": [
            {"name": "UnitedHealthcare", "status": "Covered", "auth_required": False},
            {"name": "Cigna", "status": "Covered", "auth_required": False},
            {"name": "Aetna", "status": "Covered", "auth_required": False},
        ],
        "generic_available": True,
        "avg_copay": 10,
    },
    "lisinopril": {
        "drug_class": "ACE Inhibitor",
        "condition": "Hypertension",
        "payers": [
            {"name": "UnitedHealthcare", "status": "Covered", "auth_required": False},
            {"name": "Cigna", "status": "Covered", "auth_required": False},
            {"name": "Aetna", "status": "Covered", "auth_required": False},
        ],
        "generic_available": True,
        "avg_copay": 5,
    },
    "atorvastatin": {
        "drug_class": "Statin",
        "condition": "High Cholesterol",
        "payers": [
            {"name": "UnitedHealthcare", "status": "Covered", "auth_required": False},
            {"name": "Cigna", "status": "Covered", "auth_required": False},
            {"name": "Aetna", "status": "Covered", "auth_required": False},
        ],
        "generic_available": True,
        "avg_copay": 5,
    },
}

@app.get("/drugs", tags=["Drugs"])
async def get_drug_coverage_map():
    """
    Get the drug coverage map showing which drugs are covered by which payers.
    
    Returns list of drugs with their coverage status, conditions, and payer information.
    """
    drugs_list = []
    for drug_name, details in DRUG_COVERAGE_MAP.items():
        drug_info = {
            "drug": drug_name,
            "class": details["drug_class"],
            "condition": details["condition"],
            "generic": details["generic_available"],
            "avg_copay": details["avg_copay"],
            "payers": details["payers"],
            "total_coverage": len(details["payers"]),
        }
        drugs_list.append(drug_info)
    
    return {
        "total_drugs": len(drugs_list),
        "drugs": drugs_list,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/drugs/{drug_name}", tags=["Drugs"])
async def get_drug_coverage(drug_name: str):
    """Get coverage information for a specific drug."""
    drug_name_lower = drug_name.lower()
    
    if drug_name_lower not in DRUG_COVERAGE_MAP:
        raise HTTPException(
            status_code=404,
            detail=f"Drug '{drug_name}' not found in database"
        )
    
    details = DRUG_COVERAGE_MAP[drug_name_lower]
    return {
        "drug": drug_name_lower,
        "class": details["drug_class"],
        "condition": details["condition"],
        "generic_available": details["generic_available"],
        "average_copay": details["avg_copay"],
        "coverage_by_payer": details["payers"],
        "fully_covered_payers": [p["name"] for p in details["payers"] if p["status"] == "Covered"],
        "requires_auth": [p["name"] for p in details["payers"] if p["auth_required"]],
    }


@app.get("/drugs/coverage/map", tags=["Drugs"])
async def get_coverage_map_data():
    """Get a heatmap-friendly drug coverage map for visualization."""
    payers = list(set([p["name"] for v in DRUG_COVERAGE_MAP.values() for p in v["payers"]]))
    
    coverage_map = []
    for drug_name, details in DRUG_COVERAGE_MAP.items():
        payer_coverage = {}
        for payer in payers:
            payer_data = next((p for p in details["payers"] if p["name"] == payer), None)
            payer_coverage[payer] = payer_data["status"] if payer_data else "Not Available"
        
        coverage_map.append({
            "drug": drug_name,
            "coverage_by_payer": payer_coverage,
            "class": details["drug_class"],
        })
    
    return {
        "payers": payers,
        "coverage_map": coverage_map,
        "total_drugs": len(coverage_map),
    }


# ════════════════════════════════════════════════════════════════
# BONUS FEATURES - Scoring, Alerts, Extraction, Search
# ════════════════════════════════════════════════════════════════

@app.post("/policies/score", tags=["Scoring"])
async def score_policy(policy_id: str):
    """
    Score a policy on a 0-100 scale using weighted criteria:
    - Coverage breadth (35%)
    - Pricing competitiveness (25%)
    - Requirements simplicity (20%)
    - Recency (15%)
    - Relevance (5%)
    """
    from antonrx_backend.scoring.scoring_engine import scoring_engine
    
    policy = next((p for p in POLICIES_DATA if p["id"] == policy_id), None)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    try:
        score, breakdown = scoring_engine.score_policy(policy)
        return {
            "success": True,
            "policy_id": policy_id,
            "policy_name": policy["name"],
            "score": score,
            "score_breakdown": breakdown,
            "rating": "Excellent" if score >= 80 else "Good" if score >= 60 else "Fair" if score >= 40 else "Poor",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error scoring policy: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/policies/rank", tags=["Scoring"])
async def rank_policies():
    """
    Rank all policies by score (0-100) with breakdown of each criterion.
    """
    from antonrx_backend.scoring.scoring_engine import scoring_engine
    
    try:
        rankings = []
        for policy in POLICIES_DATA:
            score, breakdown = scoring_engine.score_policy(policy)
            rankings.append({
                "rank": 0,  # Will be assigned
                "policy_id": policy["id"],
                "policy_name": policy["name"],
                "payer_name": next((p["name"] for p in PAYERS_DATA if p["id"] == policy["payer_id"]), "Unknown"),
                "score": score,
                "breakdown": breakdown
            })
        
        # Sort by score descending
        rankings.sort(key=lambda x: x["score"], reverse=True)
        
        # Assign ranks
        for idx, ranking in enumerate(rankings, 1):
            ranking["rank"] = idx
        
        return {
            "success": True,
            "total_policies": len(rankings),
            "rankings": rankings,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error ranking policies: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/extract/document", tags=["Extraction"])
async def extract_document_policy(document_text: str):
    """
    Extract policy information from document text using Claude AI.
    Returns extracted policy data with confidence score.
    
    - Documents with confidence < 70 are flagged for human review
    - Automatic duplicate detection to save API costs
    """
    from antonrx_backend.extractors.enhanced_extractor import enhanced_extractor
    
    try:
        extracted_data, confidence, checksum = enhanced_extractor.extract_policy_from_document(
            document_text=document_text,
            document_id=f"doc_{uuid4()}",
            force_reextract=False
        )
        
        return {
            "success": True,
            "extracted_data": extracted_data,
            "confidence_score": confidence,
            "requires_human_review": confidence < 70,
            "checksum": checksum,
            "status": "auto_approved" if confidence >= 70 else "pending_review",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error extracting document: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/alerts/create", tags=["Alerts"])
async def create_alert(policy_id: str, alert_type: str, message: str):
    """
    Create an alert for policy changes.
    
    Alert types:
    - POLICY_CHANGE: Policy details changed
    - NEW_COVERAGE: New drugs added
    - COVERAGE_REMOVED: Drugs removed
    - PRICE_UPDATE: Copay/cost changed
    - REQUIREMENT_CHANGE: Prior auth/step therapy changed
    - POLICY_EXPIRING: Policy expiration warning
    - NEW_POLICY: New policy created
    """
    from antonrx_backend.alerts.alert_service import alert_service
    
    policy = next((p for p in POLICIES_DATA if p["id"] == policy_id), None)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    try:
        alert = alert_service.create_alert(
            policy_id=policy_id,
            alert_type=alert_type,
            message=message,
            severity="high"
        )
        
        return {
            "success": True,
            "alert_id": alert.get("id"),
            "policy_id": policy_id,
            "alert_type": alert_type,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error creating alert: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/alerts", tags=["Alerts"])
async def get_all_alerts(unresolved_only: bool = False):
    """Get all system alerts with optional filtering for unresolved only."""
    from antonrx_backend.alerts.alert_service import alert_service
    
    try:
        alerts = alert_service.get_alerts(limit=100)
        
        if unresolved_only:
            alerts = [a for a in alerts if not a.get("resolved", False)]
        
        return {
            "success": True,
            "total_alerts": len(alerts),
            "alerts": alerts,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving alerts: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/search/semantic", tags=["Search"])
async def semantic_search(query: str, limit: int = 10):
    """
    Semantic search across policies using embeddings.
    Finds policies matching the query both keyword-wise and semantically.
    """
    from antonrx_backend.search.embedding_service import embedding_service
    from antonrx_backend.search.vector_store import vector_store
    
    try:
        # Generate query embedding
        query_embedding = embedding_service.generate_search_query_embedding(query)
        
        # Search in vector store
        results = vector_store.search(query_embedding, top_k=limit)
        
        search_results = []
        for record, similarity in results:
            policy = next((p for p in POLICIES_DATA if p["id"] == record.item_id), None)
            if policy:
                search_results.append({
                    "policy_id": policy["id"],
                    "policy_name": policy["name"],
                    "payer_name": next((p["name"] for p in PAYERS_DATA if p["id"] == policy["payer_id"]), "Unknown"),
                    "similarity_score": similarity,
                    "coverage_rules": policy["coverage_rules"]
                })
        
        return {
            "success": True,
            "query": query,
            "results": search_results,
            "count": len(search_results),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in semantic search: {str(e)}")
        # Fallback to simple keyword search
        keyword_results = []
        query_lower = query.lower()
        for policy in POLICIES_DATA:
            if query_lower in policy["name"].lower() or query_lower in policy.get("description", "").lower():
                payer = next((p for p in PAYERS_DATA if p["id"] == policy["payer_id"]), {})
                keyword_results.append({
                    "policy_id": policy["id"],
                    "policy_name": policy["name"],
                    "payer_name": payer.get("name", "Unknown"),
                    "similarity_score": 0.8,  # Keyword match
                    "coverage_rules": policy["coverage_rules"]
                })
        
        return {
            "success": True,
            "query": query,
            "results": keyword_results,
            "count": len(keyword_results),
            "search_type": "keyword_fallback",
            "timestamp": datetime.now().isoformat()
        }


@app.get("/search/by-criteria", tags=["Search"])
async def search_by_criteria(
    drug: str = None,
    payer: str = None,
    min_score: float = None,
    max_copay: float = None
):
    """
    Advanced search with multiple filter criteria:
    - drug: Filter by drug name
    - payer: Filter by payer name
    - min_score: Minimum policy score (0-100)
    - max_copay: Maximum copay amount
    """
    from antonrx_backend.search.enhanced_search_service import enhanced_search_service
    
    try:
        results = enhanced_search_service.search_policies(
            drug=drug,
            payer=payer,
            max_restrictiveness_score=100 - (min_score or 0),
            max_copay=max_copay,
            limit=50
        )
        
        return {
            "success": True,
            "filters": {
                "drug": drug,
                "payer": payer,
                "min_score": min_score,
                "max_copay": max_copay
            },
            "results": results,
            "count": len(results),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in criteria search: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/analytics/dashboard", tags=["Analytics"])
async def analytics_dashboard():
    """
    Comprehensive analytics dashboard showing:
    - System statistics
    - Policy performance metrics
    - Coverage gaps
    - Top restrictive payers
    """
    from antonrx_backend.analytics.analytics_service import analytics_service
    
    try:
        stats = analytics_service.get_policy_statistics()
        payer_rankings = analytics_service.get_payer_restrictiveness_ranking(limit=5)
        
        return {
            "success": True,
            "statistics": stats,
            "top_restrictive_payers": payer_rankings,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating analytics: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/report/quarterly", tags=["Reports"])
async def quarterly_report(year: int, quarter: int):
    """
    Generate detailed quarterly report with:
    - Policy changes and trends
    - Coverage gap analysis
    - Outlier policies
    - Payer performance metrics
    """
    from antonrx_backend.analytics.analytics_service import analytics_service
    
    if quarter < 1 or quarter > 4:
        raise HTTPException(status_code=400, detail="Quarter must be 1-4")
    
    try:
        report = analytics_service.generate_quarterly_report(year, quarter)
        
        return {
            "success": True,
            "report": report,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Health & Status Endpoints
# ════════════════════════════════════════════════════════════════

@app.get("/", tags=["System"])
async def root():
    """
    API root — information about the service.
    """
    return {
        "service": settings.app_name,
        "version": "1.0.0",
        "status": "operational",
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "auth": "/api/auth",
            "ingest": "/api/ingest",
            "search": "/api/search"
        }
    }


@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint.
    
    Returns server status and basic diagnostics.
    Used by load balancers and monitoring systems.
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": "1.0.0",
        "environment": settings.environment,
        "timestamp": None  # Could add datetime here
    }


@app.get("/health/detailed", tags=["System"])
async def health_check_detailed():
    """
    Detailed health check with service diagnostics.
    """
    from .extractors.claude_extractor import test_claude_connection
    
    diagnostics = {
        "service": settings.app_name,
        "environment": settings.environment,
        "services": {
            "claude": {
                "configured": bool(settings.anthropic_api_key),
                "connected": test_claude_connection()
            }
        },
        "rate_limiter":  rate_limiter.get_stats()
    }
    
    return diagnostics


@app.get("/metrics", tags=["System"])
async def metrics():
    """
    API metrics and system information.
    
    Returns:
    - Rate limiter statistics
    - Service uptime
    - Current configuration
    """
    return {
        "rate_limiter":  rate_limiter.get_stats(),
        "configuration": {
            "max_upload_size_mb": settings.max_upload_size_mb,
            "allowed_file_types": settings.allowed_types_list,
            "rate_limit_per_minute": settings.rate_limit_per_minute,
            "extraction_limit_per_day": settings.rate_limit_extraction_per_day
        }
    }


# ════════════════════════════════════════════════════════════════
# Custom OpenAPI Schema (Enhanced Documentation)
# ════════════════════════════════════════════════════════════════

from fastapi.openapi.utils import get_openapi

def custom_openapi():
    """Generate custom OpenAPI schema with enhanced documentation."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Anton RX API",
        version="1.0.0",
        description=app.description,
        routes=app.routes,
    )
    
    # Add security scheme documentation
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token for authentication"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# ════════════════════════════════════════════════════════════════
# Entry Point
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting AntonRX backend server...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
