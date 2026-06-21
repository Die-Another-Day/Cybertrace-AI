# CyberTrace AI
### AI-Powered Cyber Crime Investigation & Threat Correlation Platform

> Built for the Cyber Crime Branch — Smart Policing Initiative

---

## What This Platform Does

CyberTrace AI transforms isolated cybercrime complaints into actionable intelligence.
It automatically extracts entities (phone numbers, UPI IDs, emails, IPs, URLs, bank accounts)
from complaints and evidence, maps them into a Neo4j graph, and surfaces hidden connections
between cases — exposing organized scam campaigns that manual review would never catch.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Citizens / Investigators                                    │
│  React.js Web App  ←→  Flutter Mobile App                   │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTPS / REST API
┌─────────────────────▼───────────────────────────────────────┐
│  Nginx Reverse Proxy  (rate limiting, security headers)      │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│  FastAPI Backend  (Python 3.11)                              │
│  ├── Auth (JWT + RBAC)                                       │
│  ├── Complaint API                                           │
│  ├── Evidence API (OCR + STT)                                │
│  ├── Dashboard API                                           │
│  ├── Graph API                                               │
│  └── Intelligence API                                        │
└──────┬──────────────┬──────────────┬───────────────────────┘
       │              │              │
┌──────▼──┐    ┌──────▼──┐   ┌──────▼──────────────────────┐
│PostgreSQL│    │  Neo4j   │   │  Celery + Redis             │
│          │    │  Graph   │   │  ├── Complaint processing   │
│Complaints│    │  Engine  │   │  ├── Evidence OCR/STT       │
│Evidence  │    │          │   │  └── Campaign detection     │
│Users     │    │Entities  │   └─────────────────────────────┘
│Audit Logs│    │Relations │
└──────────┘    └──────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React.js 18, Vite, Tailwind CSS, Recharts |
| Backend | FastAPI, Python 3.11, Uvicorn |
| Relational DB | PostgreSQL 16 |
| Graph DB | Neo4j 5 Community |
| Task Queue | Celery + Redis |
| NLP / NER | spaCy (en_core_web_sm) + regex pipeline |
| OCR | Tesseract OCR (English + Hindi) |
| Speech-to-Text | OpenAI Whisper (base model) |
| Security | JWT, RBAC, AES-256 (Fernet/PBKDF2), SHA-256 evidence hashing |
| Deployment | Docker Compose, Nginx |

---

## Project Structure

```
cybertrace/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app entry point
│   │   ├── core/
│   │   │   ├── config.py              # Settings from .env
│   │   │   └── security.py            # JWT, AES-256, hashing
│   │   ├── db/
│   │   │   ├── postgres.py            # SQLAlchemy async engine
│   │   │   └── neo4j.py               # Neo4j driver + schema init
│   │   ├── models/
│   │   │   └── models.py              # All SQLAlchemy ORM models
│   │   ├── schemas/
│   │   │   └── schemas.py             # All Pydantic schemas
│   │   ├── api/
│   │   │   ├── deps.py                # JWT auth + RBAC deps
│   │   │   └── routes/
│   │   │       ├── auth.py            # Register, login, refresh
│   │   │       ├── complaints.py      # Complaint CRUD + processing
│   │   │       └── intelligence.py    # Dashboard, graph, evidence, audit
│   │   ├── services/
│   │   │   ├── complaint_processor.py # Full AI pipeline orchestrator
│   │   │   ├── extraction/
│   │   │   │   ├── entity_extractor.py  # NLP + regex entity extraction
│   │   │   │   └── evidence_processor.py # OCR + Whisper STT
│   │   │   ├── correlation/
│   │   │   │   └── graph_engine.py    # Neo4j threat correlation
│   │   │   └── scoring/
│   │   │       └── risk_engine.py     # ML risk scoring
│   │   └── tasks/
│   │       ├── celery_app.py          # Celery configuration
│   │       └── tasks.py               # Async task definitions
│   ├── alembic/                       # DB migrations
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── main.jsx                   # App entry + routing
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx          # Auth (login + register)
│   │   │   ├── DashboardPage.jsx      # Stats + charts + priority queue
│   │   │   ├── ComplaintsPage.jsx     # Filterable complaints list
│   │   │   ├── ComplaintDetailPage.jsx # Full detail + entities + notes
│   │   │   ├── SubmitComplaintPage.jsx # Citizen complaint form
│   │   │   ├── GraphPage.jsx          # Threat graph + campaigns
│   │   │   ├── IntelligencePage.jsx   # Ad-hoc extraction + search
│   │   │   └── AuditPage.jsx          # Audit trail viewer
│   │   ├── components/
│   │   │   └── shared/Layout.jsx      # Sidebar navigation
│   │   ├── store/authStore.js         # Zustand auth state
│   │   ├── utils/api.js               # Axios API client
│   │   └── styles/index.css           # Tailwind + design system
│   ├── Dockerfile
│   └── package.json
├── docker/
│   ├── nginx.conf                     # Reverse proxy config
│   └── init.sql                       # PostgreSQL initialization
└── docker-compose.yml                 # Full stack deployment
```

---

## Quick Start

### Prerequisites
- Docker Desktop (or Docker + Docker Compose)
- Git

### 1. Clone and configure

```bash
git clone https://github.com/your-org/cybertrace-ai.git
cd cybertrace-ai

cp backend/.env.example backend/.env
# Edit backend/.env — set SECRET_KEY, AES_ENCRYPTION_KEY, passwords
```

### 2. Generate secure keys

```bash
# Generate SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(32))"

# Generate AES_ENCRYPTION_KEY (32 chars)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Launch full stack

```bash
docker-compose up -d --build
```

### 4. Access the platform

| Service | URL |
|---|---|
| **CyberTrace AI App** | http://localhost |
| API Documentation | http://localhost:8000/api/docs |
| Neo4j Browser | http://localhost:7474 |
| Backend direct | http://localhost:8000 |

### 5. Create first admin account

```bash
# Register via API
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Admin Officer",
    "email": "admin@cybercrime.gov.in",
    "password": "Admin@1234",
    "role": "admin",
    "badge_number": "CCB/2024/001",
    "department": "Cyber Crime Branch"
  }'
```

---

## Development Setup (without Docker)

### Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Copy and configure env
cp .env.example .env
# Edit .env with your local DB credentials

# Run database migrations
alembic upgrade head

# Start backend
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev    # → http://localhost:3000
```

### Start Celery worker (optional — for background tasks)

```bash
cd backend
celery -A app.tasks.celery_app worker --loglevel=info
```

---

## API Overview

All endpoints require `Authorization: Bearer <token>` except auth routes.

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/api/v1/auth/register` | Public | Create account |
| POST | `/api/v1/auth/login` | Public | Get JWT tokens |
| GET | `/api/v1/auth/me` | Auth | Current user |
| POST | `/api/v1/complaints/` | Auth | Submit complaint |
| GET | `/api/v1/complaints/` | Auth | List complaints |
| GET | `/api/v1/complaints/{id}` | Auth | Complaint detail |
| POST | `/api/v1/complaints/{id}/process` | Investigator | Trigger AI analysis |
| GET | `/api/v1/complaints/{id}/entities` | Auth | Extracted entities |
| GET | `/api/v1/complaints/{id}/related` | Investigator | Linked cases |
| POST | `/api/v1/evidence/upload/{id}` | Auth | Upload evidence |
| GET | `/api/v1/dashboard/stats` | Investigator | Platform statistics |
| GET | `/api/v1/dashboard/priority-queue` | Investigator | Priority complaints |
| GET | `/api/v1/dashboard/trends` | Investigator | Trend data |
| GET | `/api/v1/graph/full` | Investigator | Full graph data |
| GET | `/api/v1/graph/campaigns` | Investigator | Detected campaigns |
| GET | `/api/v1/graph/stats` | Investigator | Graph statistics |
| GET | `/api/v1/intelligence/search-entity` | Investigator | Cross-case search |
| POST | `/api/v1/intelligence/extract-text` | Investigator | Ad-hoc extraction |
| GET | `/api/v1/audit/logs` | Investigator | Audit trail |

Full interactive docs: http://localhost:8000/api/docs

---

## User Roles

| Role | Permissions |
|---|---|
| **Citizen** | Submit complaints, view own complaints, add public notes |
| **Investigator** | All citizen + view all complaints, assign cases, run AI analysis, access graph and intelligence |
| **Supervisor** | All investigator + manage investigators, override risk scores |
| **Admin** | Full platform access |

---

## Security Architecture

- **JWT Authentication** — short-lived access tokens (60 min) + refresh tokens (7 days)
- **Role-Based Access Control** — enforced at every API endpoint via FastAPI dependencies
- **AES-256 Encryption** — sensitive fields encrypted at rest (Fernet/PBKDF2HMAC)
- **SHA-256 Evidence Hashing** — every uploaded file is hashed for chain-of-custody
- **Immutable Audit Trail** — every action logged with user, timestamp, IP, resource
- **Rate Limiting** — Nginx-level + SlowAPI middleware on sensitive endpoints
- **Anonymous Submissions** — citizen option to submit without identity disclosure

---

## Entity Types Extracted

| Entity | Examples | Extraction Method |
|---|---|---|
| Phone Number | `+91 98765 43210` | phonenumbers lib + regex |
| UPI ID | `name@paytm`, `id@okaxis` | regex (50+ UPI handles) |
| Email Address | `fraud@gmail.com` | regex + validation |
| URL | `http://fake-bank.xyz` | regex |
| IP Address | `192.168.1.1`, IPv6 | regex |
| Bank Account | 9–18 digit numbers | context-aware regex |
| IFSC Code | `SBIN0001234` | regex |
| Social Handle | `@username`, FB/IG/TG links | regex |
| Domain | `fake-kyc.com` | tldextract |
| Keyword | urgency/impersonation terms | keyword dictionary |

---

## Deployment Notes

- All services run in Docker containers
- Uploads stored in a Docker volume (`uploads_data`) — persistent across restarts
- PostgreSQL and Neo4j data are persisted in named volumes
- For production: enable HTTPS via Let's Encrypt, set strong passwords in `.env`
- Neo4j Bloom can be connected for rich graph visualization (requires Neo4j AuraDB or Enterprise)

---

## License

Built for the Smart Policing Hackathon — Cyber Crime Branch use case.

**ARQADEX / CyberTrace AI — 2025**
