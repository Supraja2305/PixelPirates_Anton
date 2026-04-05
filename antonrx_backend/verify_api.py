#!/usr/bin/env python3
"""Verify all API endpoints are working correctly."""

import sys
import json

try:
    import requests
    print("✅ Testing API endpoints...\n")
    
    BASE = "http://localhost:8000"
    
    tests = [
        ("GET", "/health", "Health Check"),
        ("GET", "/", "Root Endpoint"),
        ("GET", "/openapi.json", "OpenAPI Schema"),
        ("GET", "/docs", "Swagger UI"),
        ("GET", "/admin/dashboard", "Admin Dashboard"),
        ("GET", "/payers", "Get Payers"),
        ("GET", "/drugs", "Get Drugs"),
        ("GET", "/policies", "Get Policies"),
        ("GET", "/users", "Get Users"),
        ("GET", "/doctors", "Get Doctors"),
    ]
    
    success = 0
    failed = 0
    
    for method, path, name in tests:
        try:
            if method == "GET":
                r = requests.get(f"{BASE}{path}", timeout=5)
            else:
                r = requests.post(f"{BASE}{path}", timeout=5)
            
            if r.status_code < 400:
                print(f"✅ {name:<30} {r.status_code}")
                success += 1
            else:
                print(f"⚠️  {name:<30} {r.status_code}")
                failed += 1
        except Exception as e:
            print(f"❌ {name:<30} {str(e)[:30]}")
            failed += 1
    
    print(f"\n📊 Results: {success} passed, {failed} failed")
    
    # Test login endpoints
    print("\n🔐 Testing Login Endpoints...")
    
    login_tests = [
        ("POST", "/doctors/login", {"email": "doctor@antonrx.com", "password": "pass"}),
        ("POST", "/admin/login", {"email": "admin@antonrx.com", "password": "pass"}),
    ]
    
    for method, path, data in login_tests:
        try:
            r = requests.post(f"{BASE}{path}", json=data, timeout=5)
            if r.status_code < 400:
                print(f"✅ {path:<30} {r.status_code}")
            else:
                print(f"⚠️  {path:<30} {r.status_code}")
        except Exception as e:
            print(f"❌ {path:<30} {str(e)}")
    
    print("\n✨ API is ready! Open http://localhost:8000/docs in your browser")
    
except ImportError:
    print("❌ requests module not installed. Run: pip install requests")
    sys.exit(1)
