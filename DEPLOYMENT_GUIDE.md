# DEPLOYMENT_GUIDE.md

# Anton RX Backend - Deployment Guide

## Overview
AntonRX is a FastAPI-based backend for medical benefit drug policy analysis, comparison, and tracking.

## Prerequisites
- Python 3.11+
- pip or poetry for dependency management
- Environment variables configured (.env file)

## Local Development

### Setup
```bash
# Clone the repository
git clone <repository-url>
cd PixelPirates_Anton

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r antonrx_backend/requirements.txt

# Configure environment
cp .env.example .env  # Edit with your settings
```

### Running Locally
```bash
cd antonrx_backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Server will be available at: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Drug Coverage Map: `http://localhost:8000/drugs`

## Environment Variables

Create a `.env` file:
```
# OpenAI
OPENAI_API_KEY=sk-proj-xxxxx

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=xxxxx
SUPABASE_SERVICE_ROLE_KEY=xxxxx

# Application
SECRET_KEY=your-secret-key
DEBUG=true
ENVIRONMENT=development
```

## Docker Deployment

### Build
```bash
docker build -t antonrx-backend:latest .
```

### Run
```bash
docker run -d \
  --name antonrx \
  -p 8000:8000 \
  --env-file .env \
  antonrx-backend:latest
```

## Production Deployment

### Cloud Deployment Options

#### 1. Heroku
```bash
heroku create antonrx-backend
heroku config:set OPENAI_API_KEY=sk-proj-xxxxx
git push heroku main
```

#### 2. Google Cloud Run
```bash
gcloud run deploy antonrx-backend \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=sk-proj-xxxxx
```

#### 3. AWS Lambda + API Gateway
Deploy using AWS SAM or Zappa

#### 4. Railway
```bash
railway link
railway deploy
```

## API Endpoints

### Main Features
- **Authentication**: `/api/auth/register`, `/api/auth/login`, `/api/auth/me`
- **Drug Coverage Map**: `/drugs`, `/drugs/{drug_name}`, `/drugs/coverage/map`
- **Document Ingestion**: `/api/ingest` (upload policy documents)
- **Search**: `/api/search` (semantic search across policies)
- **Comparison**: `/api/compare` (compare policies)

### Documentation
Full API documentation available at `/docs` (Swagger UI)

## Monitoring & Logs

```bash
# View logs
docker logs antonrx

# Real-time monitoring
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info
```

## Performance Optimization

- Enable gzip compression in reverse proxy
- Configure Redis for caching (optional)
- Use environment-specific settings
- Set appropriate worker processes: `workers = 4 * CPU_count`

## Security Checklist

- [ ] Rotate SECRET_KEY in production
- [ ] Use HTTPS only
- [ ] Set CORS origins appropriately
- [ ] Enable rate limiting
- [ ] Use environment variables for sensitive data
- [ ] Implement API authentication
- [ ] Set security headers
- [ ] Regular dependency updates

## Troubleshooting

### ModuleNotFoundError
```bash
pip install -r antonrx_backend/requirements.txt
```

### Port Already in Use
```bash
# On Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# On Linux/Mac
lsof -i :8000
kill -9 <PID>
```

### Database Connection Issues
- Verify Supabase credentials
- Check network connectivity
- Ensure connection pooling is configured

## Maintenance

### Regular Tasks
1. Monitor application logs
2. Update dependencies monthly
3. Review and optimize slow queries
4. Backup database regularly
5. Test recovery procedures

### Updates
```bash
pip list --outdated
pip install --upgrade package-name
```

## Support
For issues, see TROUBLESHOOTING.md or open an issue in the repository.
