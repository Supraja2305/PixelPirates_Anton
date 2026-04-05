# PixelPirates_Anton Polarix: Drug Policy Intelligence Platform

> AI-powered ingestion, extraction, and comparison of insurance drug coverage policies for clinicians and payer analysts.

---

## Overview

Polarix automates the full lifecycle of medical benefit drug policy management:

1. **Ingest** — Upload PDFs, Word docs, or audio recordings of policy documents
2. **Extract** — Claude AI parses unstructured text into structured coverage data
3. **Normalize** — Standardize criteria across payers for apples-to-apples comparison
4. **Monitor** — Detect policy changes and alert users when coverage criteria shift
5. **Query** — Ask plain-language questions via the AI chat assistant

---

## Features

| Feature | Description |
|---|---|
| Multi-format document ingestion | PDF, DOCX, audio (MP3/WAV/M4A/WEBM/OGG/FLAC) |
| AI-powered policy extraction | Claude API parses unstructured policies into structured coverage data |
| Cross-payer normalization | Standardizes clinical criteria text across 8+ major payers |
| Interactive AI chat assistant | Plain-language Q&A grounded in policy documents |
| Advanced search & filtering | Filter by drug, payer, coverage status, clinical criteria |
| Graphical coverage view | Visual coverage status across payers at a glance |
| Comparison views | Side-by-side policy diff across payers |
| Speech-to-text | Upload audio for transcription and policy extraction |
| Change detection & alerting | Webhooks and notifications when coverage criteria change |
| Version history | Full audit trail of policy versions and field overrides |
| User roles & permissions | Clinician and payer analyst role-based access |
| Admin controls | Soft delete, bulk archive, field overrides, re-extraction triggers |

---

## Tech Stack

### Frontend
| Layer | Technology |
|---|---|
| Framework | Next.js 15 (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS v4 |
| Components | shadcn/ui |
| Fonts | DM Serif Display · IBM Plex Sans · IBM Plex Mono |
| Analytics | Vercel Analytics (production only) |

### Backend
| Layer | Technology |
|---|---|
| Framework | FastAPI (Python) |
| AI Extraction | Anthropic Claude API |
| Database | Firestore |
| Auth | JWT middleware |
| PDF Parsing | pdfplumber (primary) · PyMuPDF/fitz (fallback) · pytesseract (OCR fallback) |
| Speech-to-Text | `speech_to_text_service` — async + webhook delivery |
| Webhooks | `webhook_service` — event-driven delivery with retry |

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- Firestore project configured
- Anthropic API key

### Frontend

```bash
npm install
npm run dev        # http://localhost:3000
```

### Backend

```bash
cd antonrx_backend
pip install -r requirements.txt
uvicorn antonrx_backend.main:app --reload   # http://localhost:8000
```

---

## Environment Variables

### Frontend (`.env.local`)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend (`.env`)

```env
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
FIREBASE_PROJECT_ID=your-project-id
JWT_SECRET=your-secret
```

---

## API Reference

### Drug Coverage

```
GET /api/drug/{drug_name}
```

Returns all payer policies for a drug, ranked from least to most restrictive. Handles brand/generic aliases — `Humira` and `adalimumab` both resolve to the same canonical drug.

**Response**
```json
{
  "drug": "adalimumab",
  "policies_found": 6,
  "policies": [{ "payer": "UHC", "restrictiveness_score": 0.42 }]
}
```

### Speech-to-Text

| Method | Path | Description |
|---|---|---|
| `POST` | `/speech-to-text/upload` | Upload audio; sync or async (with webhook) |
| `GET` | `/speech-to-text/status/{job_id}` | Poll job status |
| `POST` | `/speech-to-text/batch` | Batch upload multiple files |
| `GET` | `/speech-to-text/batch/{batch_id}` | Batch status |
| `POST` | `/speech-to-text/webhook/register` | Register webhook for transcription events |
| `GET` | `/speech-to-text/cache-stats` | Cache statistics |
| `DELETE` | `/speech-to-text/cache` | Clear transcription cache |

Supported audio formats: `mp3` `wav` `m4a` `webm` `ogg` `flac` · Max file size: 25 MB

---

## Design Tokens

All brand values live as CSS custom properties in `globals.css` and are available as Tailwind utilities via `@theme inline`.

| Token | Value | Tailwind class | Usage |
|---|---|---|---|
| `--navy` | `#0D1B2A` | `bg-navy` | Sidebar, left panel |
| `--navy-light` | `#1A2E42` | `bg-navy-light` | Sidebar hover, dark cards |
| `--off-white` | `#F7F5F0` | `bg-off-white` | Page background |
| `--ink` | `#1C1C1E` | `text-ink` | Primary text |
| `--muted-text` | `#6B7280` | `text-muted-text` | Secondary text |
| `--covered` | `#16A34A` | `text-covered` | Coverage: covered |
| `--conditional` | `#D97706` | `text-conditional` | Coverage: conditional / PA required |
| `--restricted` | `#DC2626` | `text-restricted` | Coverage: restricted / excluded |
| `--accent-blue` | `#2563EB` | `text-accent-blue` | CTAs, focus rings, links |

Dark mode is class-based — add `dark` to `<html>` to activate.

---

## Routing

| Path | Description |
|---|---|
| `/` | Landing — role selection (clinician or payer analyst) |
| `/login?role=clinician` | Auth pre-filled for clinician |
| `/login?role=analyst` | Auth pre-filled for payer analyst |
| `/dashboard` | App shell — accessible in demo mode without credentials |

---

## Key Modules

### Criteria Normalizer (`criteria_normalizer.py`)

Standardizes clinical criteria text across payers so equivalent requirements can be compared programmatically.

```
UHC:   "Patient must have tried and failed methotrexate"
Cigna: "Inadequate response or intolerance to MTX"
Aetna: "Failure of conventional DMARD therapy (e.g., MTX)"
       ↓
       "Step therapy: prior DMARD failure required"
```

Classifies each criterion into one of: `PRIOR_AUTH`, `STEP_THERAPY`, `DIAGNOSIS_REQUIRED`, `LAB_REQUIRED`, `PRESCRIBER_SPECIALTY`, `SITE_OF_CARE`, `QUANTITY_LIMIT`, `AGE_RESTRICTION`, or `OTHER`.

### PDF Parser (`pdf_parser.py`)

Three-tier extraction with automatic fallback:

1. **pdfplumber** — primary, confidence 0.9
2. **PyMuPDF / fitz** — fallback, confidence 0.85
3. **pytesseract OCR** — last resort for scanned documents

### Admin Service (`admin_service.py`)

Full admin control surface:

- `soft_delete_policy` / `restore_policy` — toggle `is_active` without permanent deletion
- `bulk_archive_payer` / `bulk_archive_payers` — archive all policies for one or many payers at once
- `override_policy_field` — manually correct Claude extraction errors with full audit trail
- `start_re_extraction` — re-run Claude extraction with an updated prompt
- `flag_outlier_policy` — Z-score–based outlier detection (flags ≥ 2 std devs from mean)
- `get_audit_logs` / `get_audit_summary` — queryable, filterable audit history

---

## User Roles

| Role | Access |
|---|---|
| **Clinician** | Drug lookup, coverage criteria, AI chat assistant |
| **Payer Analyst** | All clinician access + policy comparison, change tracking, analytics |
| **Admin** | All access + document ingestion, field overrides, audit logs, bulk operations |

---

## Webhook Events

Polarix emits webhook events for async integrations:

| Event | Trigger |
|---|---|
| `transcription.completed` | Audio transcription finished |
| `transcription.error` | Transcription failed |
| `policy.updated` | Policy change detected |
| `policy.archived` | Policy soft-deleted or payer bulk-archived |

Register a webhook endpoint via `POST /speech-to-text/webhook/register`.

---

## Security

- JWT-based authentication on all `/api/*` routes
- Role-based access control enforced at the middleware layer
- All admin actions written to a tamper-evident audit log
- Soft deletes only — no destructive data operations
- Outlier detection flags statistically anomalous policies for human review
- Environment secrets never committed (`.env` gitignored)
