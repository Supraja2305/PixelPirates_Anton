# DEPLOYMENT_GUIDE.md
# ============================================================
# AntonRX Backend Deployment Guide
# Complete instructions for development, staging, and production
# ============================================================

## Table of Contents
1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Local Development](#local-development)
4. [Docker Deployment](#docker-deployment)
5. [Production Setup](#production-setup)
6. [Database Setup](#database-setup)
7. [Monitoring & Alerts](#monitoring--alerts)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1-Minute Local Setup
```bash
cd antonrx_backend
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys
python -m uvicorn main:app --reload
```

Visit `http://localhost:8000/docs` for API documentation.

---

## Prerequisites

### Required
- **Python 3.13+** - [python.org](https://www.python.org/)
- **OpenAI API Key** - GPT-4 Turbo access
- **Supabase Account** - Free tier available at [supabase.io](https://supabase.io)
- **Tesseract OCR** - For document parsing
  - Windows: Download installer or use `choco install tesseract`
  - macOS: `brew install tesseract`
  - Linux: `apt-get install tesseract-ocr`

### Optional but Recommended
- **Docker & Docker Compose** - For containerized deployment
- **Redis** - For distributed caching
- **PostgreSQL Client** - For database debugging

---

## Local Development

### 1. Clone and Setup

```bash
git clone <repo>
cd PixelPirates_Anton/antonrx_backend
python -m venv venv
source venv/Scripts/activate  # or: venv\Scripts\activate (Windows)
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with:
# - OPENAI_API_KEY from OpenAI
# - SUPABASE_URL and keys from Supabase dashboard
# - SECRET_KEY (generate: python -c "import secrets; print(secrets.token_urlsafe(32))")
```

### 3. Run Development Server

```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Access Services

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

### 5. Test Configuration

```bash
python config.py
# Should output all settings successfully loaded
```

---

## Docker Deployment

### Prerequisites
```bash
docker --version   # Should be 20.10+
docker-compose --version  # Should be 1.29+
```

### Option 1: Docker Compose (Recommended)

```bash
cd antonrx_backend

# Create environment file
cp .env.example .env
# Edit .env with actual values

# Build and start services
docker-compose up --build -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

### Option 2: Docker Build + Run

```bash
# Build image
docker build -t antonrx-backend:latest .

# Run container
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e SUPABASE_URL=$SUPABASE_URL \
  -e SUPABASE_KEY=$SUPABASE_KEY \
  antonrx-backend:latest

# Or with .env file
docker run -p 8000:8000 --env-file .env antonrx-backend:latest
```

### Docker Deployment Checklist
- [ ] Image builds without errors
- [ ] Container starts and health check passes
- [ ] `/health` endpoint returns 200
- [ ] `/docs` is accessible
- [ ] Environment variables loaded correctly
- [ ] Database connection established
- [ ] File uploads directory is writable
- [ ] Rate limiting initialized

---

## Production Setup

### 1. Infrastructure Requirements

**Compute**
- Minimum: 1 CPU, 2GB RAM (low traffic)
- Recommended: 2-4 CPU, 4-8GB RAM (production)
- Auto-scale: 3-10 replicas based on load

**Database**
- Supabase free tier for testing
- Supabase Pro ($25/month) for production
- Or PostgreSQL 14+ with pgvector extension

**Storage**
- Cloud storage (AWS S3, GCP, Azure Blob) for reliability
- Or persistent volumes with backup strategy

### 2. Environment Configuration

```bash
# Production .env
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# Security hardening
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
ALLOW_CREDENTIALS=true
```

### 3. Deploy via Container Orchestration

**Kubernetes Example**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: antonrx-backend
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: backend
        image: antonrx-backend:v1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: openai
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
```

**Or Heroku/Railway/Render**
```bash
# Railway deployment
railway up

# Render deployment (add render.yaml to repo)
# Connect repo, set environment, deploy
```

### 4. SSL/TLS Certificate
```bash
# Let's Encrypt (free)
certbot certonly --standalone -d yourdomain.com
```

### 5. Monitoring Setup
```bash
# Enable Prometheus metrics
PROMETHEUS_ENABLED=true

# Optional: Sentry for error tracking
SENTRY_DSN=https://key@sentry.io/project
```

---

## Database Setup

### 1. Create Supabase Tables

```sql
-- Users table
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(50) DEFAULT 'user',
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Policies table
CREATE TABLE policies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  payer_name VARCHAR(255) NOT NULL,
  drug_name VARCHAR(255) NOT NULL,
  coverage_status VARCHAR(50) NOT NULL,
  extracted_text TEXT,
  metadata JSONB,
  version INTEGER DEFAULT 1,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Embeddings table (for vector search)
CREATE TABLE embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  policy_id UUID REFERENCES policies(id),
  embedding vector(1536),
  embedding_type VARCHAR(50),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Alert subscriptions
CREATE TABLE alert_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  drug_name VARCHAR(255),
  payer_name VARCHAR(255),
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_policies_drug ON policies(drug_name);
CREATE INDEX idx_policies_payer ON policies(payer_name);
CREATE INDEX idx_users_email ON users(email);
```

### 2. Enable Supabase Extensions

In Supabase dashboard:
1. Create new project
2. Go to SQL Editor
3. Run `CREATE EXTENSION IF NOT EXISTS vector;`
4. Run above table creation scripts

### 3. Vector Search Setup

```sql
-- Create RPC function for similarity search
CREATE OR REPLACE FUNCTION search_similar_policies(
  query_embedding vector(1536),
  similarity_threshold float DEFAULT 0.3,
  match_count int DEFAULT 5
) RETURNS TABLE(
  id uuid,
  payer_name text,
  drug_name text,
  similarity float
) AS $$
  SELECT
    p.id,
    p.payer_name,
    p.drug_name,
    1 - (e.embedding <=> query_embedding) as similarity
  FROM policies p
  JOIN embeddings e ON p.id = e.policy_id
  WHERE 1 - (e.embedding <=> query_embedding) > similarity_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
$$ LANGUAGE sql;
```

---

## Monitoring & Alerts

### 1. Health Checks

```bash
# Simple health check
curl http://localhost:8000/health

# Detailed diagnostics
curl http://localhost:8000/health/detailed

# View metrics
curl http://localhost:8000/metrics
```

### 2. Log Aggregation

```bash
# View container logs
docker-compose logs -f backend

# View specific service
docker logs antonrx-backend -f --tail 100

# JSON structured logging
# All logs include: timestamp, level, service, message, context
```

### 3. Performance Monitoring

Access at http://localhost:8000/metrics for:
- Request rates
- Response times
- Error rates
- Extraction metrics
- Cache performance

### 4. Alert Triggers

- Error rate > 5% in 5 minutes
- Response time > 5 seconds average
- Database connection failures
- API key expiration warning
- Rate limit exhaustion per user

---

## Troubleshooting

### Issue: "Module not found" errors

```bash
# Ensure virtual environment is activated
source venv/Scripts/activate  # Windows: venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Issue: Tesseract not found

```bash
# Windows: Install executable
choco install tesseract
# Or download: https://github.com/UB-Mannheim/tesseract/wiki

# macOS
brew install tesseract

# Linux (Ubuntu/Debian)
apt-get install tesseract-ocr

# Add to PATH in .env if needed
TESSERACT_PATH=/path/to/tesseract
```

### Issue: Supabase connection fails

```bash
# Check credentials in .env
cat .env | grep SUPABASE

# Test connection
python -c "from storage.supabase_client import SupabaseClient; c = SupabaseClient(); print(c.test_connection())"

# Verify Supabase project is active
# (Check Supabase dashboard for status)
```

### Issue: Docker build fails

```bash
# Clear cache and rebuild
docker system prune -a
docker-compose build --no-cache

# Check disk space
docker system df
```

### Issue: Rate limit exceeded

```bash
# Check rate limit settings in .env
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_EXTRACTION_PER_DAY=1000

# Or use admin endpoint to reset
curl -X POST http://localhost:8000/admin/reset-rate-limit?user_id=user123 \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## Security Checklist

- [ ] Change SECRET_KEY in production
- [ ] Use HTTPS in production (SSL certificate)
- [ ] Disable DEBUG mode
- [ ] Restrict CORS origins
- [ ] Rotate API keys regularly
- [ ] Enable database backups
- [ ] Use strong passwords for database
- [ ] Log all administrative actions
- [ ] Monitor error logs for suspicious activity
- [ ] Keep dependencies updated (`pip list --outdated`)

---

## Performance Optimization

### 1. Caching
- Enable Redis for multi-instance deployments
- Cache frequent queries (drug policies, payers)
- TTL: 1 hour (policies), 24 hours (metadata)

### 2. Database
- Index frequently queried fields
- Use LIMIT on large queries
- Archive old policy versions

### 3. Extraction
- Limit document size to 10MB
- Use concurrent OCR for multiple pages
- Batch API calls to OpenAI

### 4. Deployment
- Use CDN for static assets
- Enable compression (gzip)
- Use production ASGI server (Gunicorn + Uvicorn)

---

## Contact & Support

- Issues: GitHub Issues
- Documentation: `/docs` (Swagger UI)
- Health Status: `/health`

---

**Last Updated**: January 2026
**Version**: 1.0.0
