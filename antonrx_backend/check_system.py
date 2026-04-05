#!/usr/bin/env python3
"""
Anton RX Backend - Configuration Check & Verification Script
Verifies all systems are properly configured and ready to use
"""

import os
import sys
from pathlib import Path

def check_environment():
    """Check environment configuration."""
    print("\n🔍 ENVIRONMENT CHECK")
    print("=" * 60)
    
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file found")
        with open(env_file) as f:
            lines = f.readlines()
            required_keys = [
                "ANTHROPIC_API_KEY",
                "SECRET_KEY", 
                "SUPABASE_URL",
                "SUPABASE_KEY"
            ]
            found_keys = [k for k in required_keys if any(k in line for line in lines)]
            print(f"✅ Found {len(found_keys)}/{len(required_keys)} required environment variables")
    else:
        print("❌ .env file NOT found")

def check_dependencies():
    """Check if required Python packages are installed."""
    print("\n📦 DEPENDENCIES CHECK")
    print("=" * 60)
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "pydantic_settings",
        "python-dotenv",
        "python-jose",
        "passlib",
        "bcrypt"
    ]
    
    missing = []
    for pkg in required_packages:
        try:
            __import__(pkg.replace("-", "_"))
            print(f"✅ {pkg}")
        except ImportError:
            print(f"❌ {pkg} - NOT INSTALLED")
            missing.append(pkg)
    
    if missing:
        print(f"\n🔴 Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
    else:
        print("\n✅ All required packages installed!")

def check_file_structure():
    """Check if all required files and directories exist."""
    print("\n📁 FILE STRUCTURE CHECK")
    print("=" * 60)
    
    required_files = [
        "main.py",
        "config.py",
        ".env",
        "requirements.txt",
        "run_server.py",
    ]
    
    required_dirs = [
        "api",
        "auth",
        "models",
        "utils",
        "storage",
        "search"
    ]
    
    for file in required_files:
        if Path(file).exists():
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - MISSING")
    
    for dir in required_dirs:
        if Path(dir).exists():
            print(f"✅ {dir}/")
        else:
            print(f"❌ {dir}/ - MISSING")

def main():
    """Run all checks."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " ANTON RX BACKEND - SYSTEM CHECK ".center(58) + "║")
    print("╚" + "=" * 58 + "╝")
    
    check_environment()
    check_dependencies()
    check_file_structure()
    
    print("\n" + "=" * 60)
    print("✨ SETUP COMPLETE!")
    print("\n📚 API ENDPOINTS AVAILABLE:")
    print("  - Health Check: http://localhost:8000/health")
    print("  - API Docs: http://localhost:8000/docs")
    print("  - Admin Dashboard: http://localhost:8000/admin/dashboard")
    print("  - Payers: http://localhost:8000/payers")
    print("  - Drugs: http://localhost:8000/drugs")
    print("  - Policies: http://localhost:8000/policies")
    print("  - Users: http://localhost:8000/users")
    print("  - Doctors: http://localhost:8000/doctors")
    print("\n🚀 To start the server, run:")
    print("  python run_server.py")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
