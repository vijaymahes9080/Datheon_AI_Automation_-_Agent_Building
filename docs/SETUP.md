# Setup & Installation Guide

This guide provides step-by-step instructions for installing, configuring, and running **ORBIT AI Operations Studio** in local development and production environments.

---

## 1. System Prerequisites

Before starting, ensure your host system satisfies the following prerequisites:
- **Operating System:** Windows 10/11, macOS 12+, or Ubuntu 20.04+ Linux
- **Python:** Version 3.10 or higher (Python 3.12 recommended)
- **Git:** Version 2.30 or higher
- **Modern Web Browser:** Google Chrome, Mozilla Firefox, Microsoft Edge, or Apple Safari

---

## 2. Local Environment Installation

### Step 1: Clone Repository
Clone the codebase using SSH or HTTPS:
```bash
# Clone via SSH (Recommended)
git clone git@github.com:vijaymahes9080/Datheon_AI_Automation_-_Agent_Building.git
cd Datheon_AI_Automation_-_Agent_Building/vj

# Or clone via HTTPS
git clone https://github.com/vijaymahes9080/Datheon_AI_Automation_-_Agent_Building.git
cd Datheon_AI_Automation_-_Agent_Building/vj
```

### Step 2: Create and Activate Virtual Environment
Isolate Python dependencies within a dedicated virtual environment:

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell restricts execution scripts, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first)*

**On macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies
Install all required runtime and development packages:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Configuration & Environment Variables

ORBIT uses Pydantic Settings (`core/config.py`) to manage configuration. By default, the system operates in **Demo Mode**, utilizing high-fidelity mock engines for all integrations with zero configuration required.

To connect live external services, create a `.env` file in the project root:

```ini
# ==============================================================================
# ORBIT AI Operations Studio - Environment Configuration
# ==============================================================================

# Application Environment (development, testing, production)
ORBIT_ENV=development
ORBIT_PORT=8000
ORBIT_HOST=127.0.0.1
DEBUG=true

# Database Path (defaults to SQLite local database)
DATABASE_URL=sqlite:///./orbit_studio.db

# Live Integration Toggles (false = Mock Mode, true = Live Mode)
OPENAI_ENABLED=false
AIRTABLE_ENABLED=false
SLACK_ENABLED=false
EMAIL_ENABLED=false
SHEETS_ENABLED=false
STRIPE_ENABLED=false

# OpenAI Configuration
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini

# Airtable CRM Configuration
AIRTABLE_API_KEY=patxxxxxxxxxxxxxxxx.xxxxxxxxxxxxxxxx
AIRTABLE_BASE_ID=appxxxxxxxxxxxxxx
AIRTABLE_TABLE_NAME=Leads

# Slack Configuration
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx
SLACK_SALES_CHANNEL=C0123456789
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00/B00/XXXXX

# Email Ingestion & Draft Configuration
EMAIL_IMAP_SERVER=imap.gmail.com
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_ACCOUNT=operations@company.com
EMAIL_PASSWORD=app-specific-password
EMAIL_DRAFT_ONLY=true

# Google Sheets Accounting Configuration
GOOGLE_SERVICE_ACCOUNT_JSON=./credentials/google_service_account.json
GOOGLE_SPREADSHEET_ID=1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Stripe Webhook Configuration
STRIPE_SECRET_KEY=sk_test_51xxxxxxxxxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 4. Generating Test Data & PDF Fixtures

The repository includes a fixture generator for synthetic invoice PDFs:
```bash
python generate_sample_pdfs.py
```
This command generates:
- `data/valid_sample_invoice.pdf` (Clean invoice with exact arithmetic reconciliation)
- `data/discrepant_sample_invoice.pdf` (Synthetic invoice with intentional $110 calculation error for testing audit flags)

---

## 5. Running the Application

Start the FastAPI application with Uvicorn:
```bash
python main.py
```

Expected startup terminal log:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Database tables initialized successfully.
INFO:     ORBIT Studio initialized in Demo Mode (Mock engines active).
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### Accessing the Applications:
- **Interactive Operations Studio:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive OpenAPI Documentation (Swagger UI):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Redoc Alternative API Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 6. Running the Automated Test Suite

Execute the full test suite with verbose reporting:
```bash
pytest tests/ -v
```

To run individual module tests:
```bash
# Test Lead Routing
pytest tests/test_leads.py -v

# Test Customer Support & RAG
pytest tests/test_support.py -v

# Test Invoice Intelligence & Financial Safeguards
pytest tests/test_invoices.py -v

# Test Enterprise Orchestration & Stripe Webhooks
pytest tests/test_orchestration.py -v

# Test Integration Adapters
pytest tests/test_integrations.py -v

# Test Full End-to-End Scenarios
pytest tests/test_e2e_scenarios.py -v
```

---

## 7. Troubleshooting & Common Issues

| Symptom | Cause | Resolution |
|---|---|---|
| `Address already in use` error on port 8000 | Another process is bound to port 8000 | Stop the existing process or run with custom port: `python -m uvicorn main:app --port 8080` |
| `pypdf.errors.PdfReadError` | Corrupted PDF upload or invalid format | Verify PDF has `%PDF-` header; regenerate fixtures with `python generate_sample_pdfs.py` |
| SQLite `database is locked` | High concurrent access on single thread | SQLite WAL mode is enabled automatically in `core/database.py`; ensure connection pool is not exhausted |
| PowerShell script execution disabled | Execution policy restriction on Windows | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in your PowerShell session |
