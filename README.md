# ORBIT AI Operations Studio

> **Enterprise-Grade Autonomous AI Workforce & Business Automation Studio**  
> Unifying four core business systems into a cohesive, auditable, and production-ready operational platform.

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-teal.svg)](https://fastapi.tiangolo.com)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2.8-red.svg)](https://pydantic.dev)
[![Tests](https://img.shields.io/badge/Tests-19%20Passed-brightgreen.svg)]()
[![License](https://img.shields.io/badge/License-Proprietary-purple.svg)]()

---

## 🌟 Executive Summary

**ORBIT AI Operations Studio** is a unified business automation suite built for modern agencies and high-volume eCommerce enterprises. Rather than disparate, disconnected scripts, ORBIT orchestrates four mission-critical operational divisions into a centralized operations studio:

```
+-----------------------------------------------------------------------------------------+
|                               ORBIT AI Operations Studio                                |
|   +-------------------+  +--------------------+  +------------------+  +-------------+  |
|   | 1. Lead Routing   |  | 2. Support Intel   |  | 3. Invoice Ops   |  | 4. Multi-   |  |
|   |    & Scoring      |  |    & Knowledge RAG |  |    & Reconcile   |  |    Agent    |  |
|   +---------+---------+  +---------+----------+  +--------+---------+  +------+------+  |
|             |                      |                      |                   |         |
|   +---------v----------------------v----------------------v-------------------v-----+  |
|   |              Core Engine: Audit Logger | Event Broker | SQLite DB                |  |
|   +------------------------------------+--------------------------------------------+  |
|                                        |                                                |
|   +------------------------------------v--------------------------------------------+  |
|   |                     Modular Integration Adapters                                |  |
|   |    OpenAI  |  Airtable  |  Slack  |  Email (Gmail/IMAP)  |  Sheets  |  Stripe   |  |
|   |    (Live API adapters + deterministic high-fidelity mock engines with switches) |  |
|   +------------------------------------+--------------------------------------------+  |
|                                        |                                                |
|   +------------------------------------v--------------------------------------------+  |
|   |        FastAPI Async Backend REST API & WebSockets (Port 8000)                  |  |
|   +------------------------------------+--------------------------------------------+  |
|                                        |                                                |
|   +------------------------------------v--------------------------------------------+  |
|   |        Modern Frontend Web Studio (Single Page Glassmorphism App)               |  |
|   | Operations Overview | Modules 1-4 | Workflow Studio | Approvals | Integrations  |  |
|   +---------------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------------+
```

---

## 🧩 Four Core Internship Projects

### 1. Lead Intelligence & Revenue Routing
- **Pipeline:** `Capture → Validate → Normalize → Qualify → Persist → Route → Notify → Audit`
- **Capabilities:**
  - Authenticated web forms and webhook ingestion endpoints.
  - Heuristic business rules + OpenAI structured evaluation producing qualification score (0-100), priority badges, and missing information alerts.
  - AI sales talking-point synthesis.
  - Idempotent Airtable CRM record creation and rich Slack Block Kit alerts.
  - Sub-second pipeline execution with latency measurements (SLA: < 10.0s).

### 2. Customer Support & Email Intelligence
- **Pipeline:** `Receive → Classify → Assess → Retrieve → Draft → Review → Label → Audit`
- **Capabilities:**
  - Automated classification across 8 business intents (Billing, Tech Support, Account Access, Product Inquiries, Complaints, Urgent Incidents, Spam, Unknown).
  - Grounded RAG knowledge retrieval strictly restricted to approved operational policies (zero hallucination).
  - **Draft-only default safety:** Automated dispatches are blocked at code level until staff authorization.
  - Mandatory human escalation gates for refunds, legal matters, account deletions, and system outages.
  - Prompt injection neutralization against delimiter overrides.

### 3. Invoice Intelligence & Financial Operations
- **Pipeline:** `Upload → Inspect → Extract → Validate → Reconcile → Approve → Export → Audit`
- **Capabilities:**
  - Secure PDF document ingestion with `%PDF-` header validation and size guards.
  - Line items, subtotal, tax rate, tax amount, discounts, and total extraction.
  - Mathematical discrepancy audit (`subtotal - discount + tax == total` within $0.05 tolerance).
  - Duplicate invoice detection via SHA-256 file fingerprinting and vendor/invoice number combinations.
  - Human review gate enforcement prior to Google Sheets financial export.

### 4. Enterprise Multi-Agent Business Orchestration
- **Pipeline:** `Intake → Contract Drafting → Approval Gate → Stripe HMAC → Slack Provisioning → Executive Digest`
- **Capabilities:**
  - Stable sequential project code allocation (`PRJ-2026-001`).
  - Template-governed Master Services Agreement drafting with parameter validation (no hallucinated clauses).
  - Cryptographic Stripe webhook HMAC-SHA256 signature verification with constant-time comparison and 5-minute replay attack defense.
  - Automated Slack collaboration channel provisioning (`#prj-...`).
  - Weekly operational executive digest grounded strictly in stored database metrics.

---

## 🚀 Quickstart & Installation

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Node.js 18+ (optional, for frontend toolchains)
- Git

### 1. Clone & Setup Environment
```bash
git clone git@github.com:vijaymahes9080/Datheon_AI_Automation_-_Agent_Building.git
cd Datheon_AI_Automation_-_Agent_Building
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run Application
```bash
python main.py
# Server starts at http://127.0.0.1:8000
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser to access the interactive Operations Studio.

### 3. Run Test Suite
```bash
pytest tests/ -v
# 19/19 tests passing across all four modules and e2e scenarios
```

---

## 📚 Complete Documentation Suite

Detailed architecture specifications, security matrices, setup guides, and walkthroughs are available in `docs/`:

- [docs/ARCHITECTURE.md](file:///d:/intership/Datheon_AI_Automation_-_Agent_Building/vj/docs/ARCHITECTURE.md) — System topology, domain entities, and data models.
- [docs/SETUP.md](file:///d:/intership/Datheon_AI_Automation_-_Agent_Building/vj/docs/SETUP.md) — Local installation, environment variables, and Docker deployment.
- [docs/INTEGRATIONS.md](file:///d:/intership/Datheon_AI_Automation_-_Agent_Building/vj/docs/INTEGRATIONS.md) — Setup and credentials for OpenAI, Airtable, Slack, Sheets, Stripe, and n8n.
- [docs/SECURITY.md](file:///d:/intership/Datheon_AI_Automation_-_Agent_Building/vj/docs/SECURITY.md) — Defense-in-depth, prompt injection defenses, and HMAC verification.
- [docs/TESTING.md](file:///d:/intership/Datheon_AI_Automation_-_Agent_Building/vj/docs/TESTING.md) — Test matrix, mock vs live test procedures, and test coverage.
- [docs/DEMO_GUIDE.md](file:///d:/intership/Datheon_AI_Automation_-_Agent_Building/vj/docs/DEMO_GUIDE.md) — Step-by-step walkthrough of the 14 mandatory demo scenarios.
- [docs/CLIENT_ONBOARDING.md](file:///d:/intership/Datheon_AI_Automation_-_Agent_Building/vj/docs/CLIENT_ONBOARDING.md) — Client handover protocol and production checklist.
- [docs/VIDEO_WALKTHROUGH.md](file:///d:/intership/Datheon_AI_Automation_-_Agent_Building/vj/docs/VIDEO_WALKTHROUGH.md) — Video demonstration script and talking points.
