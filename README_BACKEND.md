# Anton RX Backend - Medical Benefit Drug Policy Tracker

> AI-powered backend system for ingesting, parsing, extracting, and comparing medical benefit drug policies from multiple health plans.

## Features

### Core Capabilities
- **Document Parsing**: Support for PDF, HTML, Word, and image (OCR) documents
- **AI Extraction**: GPT-4 powered policy analysis and field extraction
- **Drug Coverage Mapping**: Visual heatmap of drug coverage across insurance payers
- **Policy Comparison**: Track policy changes over time and compare across payers
- **Semantic Search**: Natural language search across all policies
- **Change Tracking**: Monitor and alert on policy changes for specific drugs

### Supported Document Formats
- PDF files (text and scanned with OCR)
- HTML documents
- Microsoft Word (.docx)
- Images with OCR support

### Data Tracking
- Drug name normalization
- Payer identification
- Coverage status (Covered/Not Covered/Prior Auth)
- Pricing and copay information
- Clinical requirements and prior authorization rules
- Policy versioning and change history

## Quick Start

### Prerequisites
- Python 3.11+
- pip

### Installation
```bash
# Clone repository
git clone <repo-url>
cd PixelPirates_Anton

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r antonrx_backend/requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Running
```bash
cd antonrx_backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Access the API:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Drug Coverage Map**: http://localhost:8000/drugs
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Drug Coverage
- `GET /drugs` - Get all drug coverage information
- `GET /drugs/{drug_name}` - Get specific drug coverage
- `GET /drugs/coverage/map` - Get heatmap-compatible coverage matrix

### Example
```bash
# Get all drugs
curl http://localhost:8000/drugs

# Get specific drug
curl http://localhost:8000/drugs/adalimumab

# Get coverage map
curl http://localhost:8000/drugs/coverage/map
```

## Environment Setup

Create `.env` file:
```
# OpenAI API
OPENAI_API_KEY=sk-proj-xxxxx

# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=xxxxx

# Application
SECRET_KEY=your-secret-key
DEBUG=true
ENVIRONMENT=development
```

## Project Structure

```
antonrx_backend/
├── main.py                 # FastAPI app entry point
├── config.py              # Configuration management
├── auth/                  # Authentication & JWT
│   ├── middleware.py
│   ├── jwt_handler.py
│   └── password.py
├── api/                   # API routes
│   ├── routes.py
│   ├── auth_route.py
│   └── [feature_routes].py
├── models/                # Pydantic models
│   ├── user.py
│   ├── policy.py
│   └── responses.py
├── parsers/               # Document parsing
│   ├── pdf_parser.py
│   ├── html_parser.py
│   ├── word_parser.py
│   └── image_parser.py
├── extractors/            # AI extraction
│   ├── claude_extractor.py
│   └── prompts.py
├── normalizers/           # Data normalization
│   ├── drug_normalizer.py
│   └── criteria_normalizer.py
├── storage/               # Database operations
│   ├── firestore_client.py
│   ├── supabase_client.py
│   └── version_manager.py
├── search/                # Semantic search
│   ├── semantic_search.py
│   └── embedding_service.py
├── scoring/               # Policy scoring
│   └── scoring_engine.py
└── utils/                 # Utilities
    ├── error_handler.py
    ├── rate_limiter.py
    ├── file_security.py
    └── schema_validator.py
```

## Deployment

See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for comprehensive deployment instructions including:
- Docker deployment
- Cloud platforms (Heroku, GCP, AWS, Railway)
- Production configuration
- Security checklist

## Technologies

- **Framework**: FastAPI 0.135+
- **Server**: Uvicorn
- **Authentication**: Python-Jose, Passlib, Bcrypt
- **AI**: OpenAI GPT-4, Anthropic Claude
- **Database**: Supabase (PostgreSQL)
- **Parsing**: PyMuPDF, pdfplumber, BeautifulSoup4, python-docx
- **Search**: pgvector embeddings
- **Validation**: Pydantic

## Development

### Running Tests
```bash
pytest tests/

# With coverage
pytest --cov=antonrx_backend tests/
```

### Code Style
```bash
# Format code
black antonrx_backend/

# Lint
flake8 antonrx_backend/
```

## Performance

- Multi-format document support with fallback parsers
- Vectorized semantic search for fast policy retrieval
- Caching layer for frequently accessed policies
- Rate limiting for API protection
- Async/await throughout for high concurrency

## Security

- JWT-based authentication
- Rate limiting per user
- Input validation and sanitization
- File upload security checks
- Environment-based secrets management

## Roadmap

- [ ] Advanced policy comparison with scoring
- [ ] Real-time policy update monitoring
- [ ] Multi-language policy support
- [ ] Advanced analytics dashboard
- [ ] Integration with pharmacy benefit managers
- [ ] Mobile app support

## Troubleshooting

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

## Contributing

1. Create a feature branch
2. Commit changes
3. Push and open a pull request

## License

Proprietary - PixelPirates Hackathon Team

## Support

For support, open an issue in the repository or contact the development team.
