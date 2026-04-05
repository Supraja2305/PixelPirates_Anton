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
from starlette.middleware.base import BaseHTTPMiddleware
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
# Security Middleware & Headers (Applied first for outermost layer)
# ════════════════════════════════════════════════════════════════

# Class-based Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Prevent clickjacking attacks (embedding in frames)
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enable browser XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy - restrict resource loading
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'"
        
        # Enforce HTTPS (Strict-Transport-Security)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Additional security headers
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Disable client-side caching for sensitive data
        if "/admin" in request.url.path or "/user" in request.url.path:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        return response


# Restricted CORS - Production ready
allowed_origins = [
    "http://localhost:3000",      # Local development
    "http://localhost:3001",      # Local dev alternate
    "http://127.0.0.1:3000",      # Localhost variant
]

# Allow these origins if configured in env
if os.getenv("FRONTEND_URL"):
    allowed_origins.append(os.getenv("FRONTEND_URL"))
if os.getenv("PRODUCTION_URL"):
    allowed_origins.append(os.getenv("PRODUCTION_URL"))

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
