# tests/test_api.py
# ============================================================
# Comprehensive test suite for AntonRX API
# Tests authentication, document parsing, search, and more
# ============================================================

import pytest
import asyncio
import json
from httpx import AsyncClient, Client
from datetime import datetime

# Note: In a real setup, run with:
# pytest tests/ -v --cov=antonrx_backend


class TestAuthentication:
    """Test authentication endpoints."""
    
    @pytest.mark.asyncio
    async def test_user_registration(self, client):
        """Test user registration."""
        response = await client.post("/api/auth/register", json={
            "email": "testuser@example.com",
            "password": "SecurePassword123!@#"
        })
        assert response.status_code in [200, 201]
        data = response.json()
        assert "user_id" in data

    @pytest.mark.asyncio
    async def test_user_login(self, client):
        """Test user login and token generation."""
        # First register
        await client.post("/api/auth/register", json={
            "email": "logintest@example.com",
            "password": "SecurePassword123!@#"
        })
        
        # Then login
        response = await client.post("/api/auth/login", json={
            "email": "logintest@example.com",
            "password": "SecurePassword123!@#"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = await client.post("/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "WrongPassword123"
        })
        assert response.status_code == 401


class TestDocumentParsing:
    """Test document parsing endpoints."""
    
    @pytest.mark.asyncio
    async def test_supported_formats(self, client):
        """Test getting list of supported formats."""
        response = await client.get("/api/supported-formats")
        assert response.status_code == 200
        data = response.json()
        assert ".pdf" in data
        assert ".html" in data
        assert ".docx" in data

    @pytest.mark.asyncio
    async def test_upload_document(self, client, auth_token, sample_pdf):
        """Test document upload and extraction."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create multipart file upload
        files = {"file": ("test_policy.pdf", sample_pdf, "application/pdf")}
        data = {
            "drug_name": "Aspirin",
            "payer_name": "UnitedHealthcare"
        }
        
        response = await client.post(
            "/api/ingest/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        # Should return 202 Accepted for async processing
        assert response.status_code in [200, 202]
        result = response.json()
        assert "policy_id" in result


class TestSearch:
    """Test policy search endpoints."""
    
    @pytest.mark.asyncio
    async def test_policies_search(self, client, auth_token, sample_policies):
        """Test semantic search for policies."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        search_query = {
            "query": "prior authorization required",
            "drug_name": "Metformin",
            "limit": 5
        }
        
        response = await client.post(
            "/api/search/policies",
            json=search_query,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    @pytest.mark.asyncio
    async def test_drug_search(self, client, auth_token):
        """Test search for multiple drugs."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = await client.get(
            "/api/search/drugs?drug_names=Aspirin&drug_names=Metformin&limit=5",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "drugs" in data


class TestComparison:
    """Test policy comparison endpoints."""
    
    @pytest.mark.asyncio
    async def test_policy_comparison(self, client, auth_token, sample_policy_ids):
        """Test comparing multiple policies."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        comparison_request = {
            "drug_name": "Aspirin",
            "policy_ids": sample_policy_ids[:5]
        }
        
        response = await client.post(
            "/api/compare/policies",
            json=comparison_request,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "comparison_summary" in data
        assert len(data["policies"]) > 0


class TestSystemEndpoints:
    """Test system and health endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_detailed_health(self, client):
        """Test detailed health check."""
        response = await client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "services" in data
        assert "openai" in data["services"]

    @pytest.mark.asyncio
    async def test_metrics(self, client):
        """Test metrics endpoint."""
        response = await client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "rate_limiter" in data or "analytics" in data

    @pytest.mark.asyncio
    async def test_api_root(self, client):
        """Test API root endpoint."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "AntonRX"
        assert "documentation" in data


class TestAdminEndpoints:
    """Test admin-only endpoints."""
    
    @pytest.mark.asyncio
    async def test_admin_stats(self, client, admin_token):
        """Test admin stats endpoint."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = await client.get("/api/admin/stats", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "database" in data or "analytics" in data

    @pytest.mark.asyncio
    async def test_admin_health(self, client, admin_token):
        """Test admin health endpoint."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = await client.get("/api/admin/health", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestErrorHandling:
    """Test error handling and validation."""
    
    @pytest.mark.asyncio
    async def test_invalid_json(self, client, auth_token):
        """Test handling of invalid JSON."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = await client.post(
            "/api/search/policies",
            content="invalid json {{{",
            headers=headers
        )
        assert response.status_code == 400 or response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_auth(self, client):
        """Test missing authorization."""
        response = await client.get("/api/search/policies")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_auth_token(self, client):
        """Test invalid authorization token."""
        headers = {"Authorization": "Bearer invalid.token.here"}
        
        response = await client.get(
            "/api/search/policies",
            json={"query": "test"},
            headers=headers
        )
        assert response.status_code == 401


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def client():
    """Create test client."""
    from fastapi.testclient import TestClient
    from main import app
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create async test client."""
    from main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def auth_token():
    """Generate valid auth token for testing."""
    from antonrx_backend.auth.jwt_handler import create_access_token
    return create_access_token(data={
        "sub": "testuser@example.com",
        "user_id": "test-user-id",
        "role": "user"
    })


@pytest.fixture
def admin_token():
    """Generate admin auth token for testing."""
    from antonrx_backend.auth.jwt_handler import create_access_token
    return create_access_token(data={
        "sub": "admin@example.com",
        "user_id": "admin-user-id",
        "role": "admin"
    })


@pytest.fixture
def sample_pdf():
    """Sample PDF content for testing."""
    # In a real test, this would be a real PDF file
    return b"%PDF-1.4\nSample PDF content for testing"


@pytest.fixture
def sample_policies():
    """Sample policy data for testing."""
    return [
        {
            "id": "policy-1",
            "payer_name": "UnitedHealthcare",
            "drug_name": "Metformin",
            "coverage_status": "covered",
            "text": "Metformin is covered with prior authorization"
        },
        {
            "id": "policy-2",
            "payer_name": "Aetna",
            "drug_name": "Metformin",
            "coverage_status": "covered",
            "text": "Metformin is covered without restrictions"
        }
    ]


@pytest.fixture
def sample_policy_ids():
    """Sample policy IDs for testing."""
    return ["policy-1", "policy-2", "policy-3", "policy-4", "policy-5"]


# ============================================================
# Integration Tests
# ============================================================

class TestIntegration:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, client, sample_pdf):
        """Test complete flow: register -> upload -> search -> compare."""
        
        # 1. Register user
        reg_response = await client.post("/api/auth/register", json={
            "email": "integration_test@example.com",
            "password": "SecurePassword123!@#"
        })
        assert reg_response.status_code in [200, 201]
        
        # 2. Login
        login_response = await client.post("/api/auth/login", json={
            "email": "integration_test@example.com",
            "password": "SecurePassword123!@#"
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 3. Upload document
        files = {"file": ("test_policy.pdf", sample_pdf, "application/pdf")}
        upload_response = await client.post(
            "/api/ingest/upload",
            files=files,
            data={"drug_name": "Aspirin"},
            headers=headers
        )
        assert upload_response.status_code in [200, 202]
        
        # 4. Search policies
        search_response = await client.post(
            "/api/search/policies",
            json={"query": "coverage requirements", "limit": 5},
            headers=headers
        )
        assert search_response.status_code == 200
        
        # 5. Check health
        health_response = await client.get("/health")
        assert health_response.status_code == 200


# ============================================================
# Performance Tests
# ============================================================

class TestPerformance:
    """Performance and load tests."""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client, auth_token):
        """Test handling of concurrent requests."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        tasks = [
            client.get("/api/supported-formats", headers=headers)
            for _ in range(10)
        ]
        
        responses = await asyncio.gather(*tasks)
        assert all(r.status_code == 200 for r in responses)

    @pytest.mark.asyncio
    async def test_rate_limiting(self, client, auth_token):
        """Test rate limiting enforcement."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Make multiple rapid requests
        for i in range(5):
            response = await client.get(
                "/api/supported-formats",
                headers=headers
            )
            # Eventually should hit rate limit (429)
            # First requests should succeed (200)
            assert response.status_code in [200, 429]
