#!/usr/bin/env python3
"""Test script for Anton RX Backend API endpoints."""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_endpoint(method, path, name):
    """Test a specific endpoint."""
    try:
        url = f"{BASE_URL}{path}"
        if method == "GET":
            response = requests.get(url, timeout=5)
        else:
            response = requests.post(url, timeout=5)
        
        print(f"\n✅ {name}")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Data: {json.dumps(data, indent=2)[:200]}...")
    except Exception as e:
        print(f"\n❌ {name}")
        print(f"   Error: {str(e)}")

print("🧪 Testing Anton RX Backend API Endpoints")
print("=" * 60)

# Test all endpoints
test_endpoint("GET", "/", "Root Endpoint")
test_endpoint("GET", "/health", "Health Check")
test_endpoint("GET", "/admin/dashboard", "Admin Dashboard")
test_endpoint("GET", "/payers", "Get All Payers")
test_endpoint("GET", "/drugs", "Get All Drugs")
test_endpoint("GET", "/policies", "Get All Policies")
test_endpoint("GET", "/users", "Get All Users")
test_endpoint("GET", "/doctors", "Get All Doctors")
test_endpoint("GET", "/payers/p1", "Get Specific Payer")
test_endpoint("GET", "/drugs/d1", "Get Specific Drug")
test_endpoint("GET", "/drug-coverage/d1/payers", "Drug Coverage")

print("\n" + "=" * 60)
print("✨ API Testing Complete!")
print("\n📚 API Documentation: http://localhost:8000/docs")
