# Quick Start Guide

## What We Built

AntonRX Backend - A FastAPI-based medical benefit drug policy tracker with AI-powered analysis.

## Current Status

✅ **Backend Server Running**
- URL: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
- Status: Fully operational

## Active Endpoints

### Drug Coverage Map (WORKING NOW!)
```bash
# Get all drugs
GET http://localhost:8000/drugs

# Get specific drug
GET http://localhost:8000/drugs/adalimumab

# Get coverage matrix
GET http://localhost:8000/drugs/coverage/map
```

### System Health
```bash
# Health check
GET http://localhost:8000/health

# Detailed health
GET http://localhost:8000/health/detailed
```

### Available Drugs in Database
- `adalimumab` - TNF Inhibitor (Rheumatoid Arthritis)
- `metformin` - Antidiabetic (Type 2 Diabetes)
- `lisinopril` - ACE Inhibitor (Hypertension)
- `atorvastatin` - Statin (High Cholesterol)

## Quick Test

```bash
# From PowerShell or Terminal
curl http://localhost:8000/drugs

# Or with Python
python -c "
import requests
r = requests.get('http://localhost:8000/drugs')
print(r.json())
"
```

## Project Structure

```
PixelPirates_Anton/
├── antonrx_backend/          # Backend source code
│   ├── main.py              # FastAPI app with drug map endpoints
│   ├── config.py            # Configuration
│   ├── requirements.txt      # Dependencies
│   ├── auth/                # Authentication
│   ├── api/                 # API routes
│   ├── models/              # Data models
│   ├── parsers/             # Document parsing
│   └── utils/               # Utilities
├── PixelPirates_Anton/      # Frontend (Next.js/React)
├── DEPLOYMENT_GUIDE.md      # Deployment instructions
├── README_BACKEND.md        # Backend documentation
├── .gitignore              # Git ignore rules
└── README.md               # Main project README
```

## For Git Commit

```bash
git status                  # See all changes
git add .                   # Stage all changes
git commit -m "feat: Add drug coverage map API and deployment docs"
git log --oneline          # Verify commits
```

## Key Files Modified

1. `antonrx_backend/main.py` - Added drug endpoints
2. `antonrx_backend/requirements.txt` - Updated dependencies
3. `antonrx_backend/models/user.py` - Created user models
4. `antonrx_backend/parsers/pdf_parser.py` - Fixed imports
5. `antonrx_backend/parsers/html_parser.py` - Fixed imports
6. `DEPLOYMENT_GUIDE.md` - Deployment documentation
7. `README_BACKEND.md` - Backend documentation

## Next Steps

1. **Test the API**: Visit `http://localhost:8000/docs`
2. **Add Real Data**: Replace sample data in `DRUG_COVERAGE_MAP`
3. **Connect Database**: Update Supabase credentials in `.env`
4. **Deploy**: Follow `DEPLOYMENT_GUIDE.md`

## Troubleshooting

### Server not starting?
```bash
# Kill process on port 8000
lsof -i :8000
kill -9 <PID>

# Restart
python -m uvicorn antonrx_backend.main:app --host 0.0.0.0 --port 8000
```

### Missing dependencies?
```bash
pip install -r antonrx_backend/requirements.txt
```

### Port already in use?
Edit the command to use a different port:
```bash
python -m uvicorn antonrx_backend.main:app --port 8001
```

## API Documentation

Auto-generated Swagger docs available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Support

Check `DEPLOYMENT_GUIDE.md` for detailed deployment instructions and troubleshooting.
