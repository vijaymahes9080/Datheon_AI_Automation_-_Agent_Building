# System Architecture & Technical Specification

## 1. Architectural Overview

ORBIT AI Operations Studio is engineered as an enterprise-grade, asynchronous automation platform that unifies four mission-critical business automation domains into a cohesive operational control center:
1. **Lead Intelligence & Revenue Routing**
2. **Customer Support & Email Intelligence**
3. **Invoice Intelligence & Financial Operations**
4. **Enterprise Multi-Agent Business Orchestration**

The platform emphasizes strict separation of concerns, deterministic safety controls, structured AI generation, idempotency, and comprehensive auditability.

```
+-----------------------------------------------------------------------------------------+
|                                    Client Tier                                          |
|  Single-Page Application: Glassmorphism UI (HTML5, Vanilla CSS3, Async JavaScript)     |
|  Real-Time Telemetry | Approval Center | Workflow Studio | Module Workspaces            |
+--------------------------------------------+--------------------------------------------+
                                             | HTTP / REST / JSON
+--------------------------------------------v--------------------------------------------+
|                                   Application Tier                                      |
|  FastAPI Async ASGI Server (Python 3.12, Uvicorn)                                       |
|  +-----------------------------------------------------------------------------------+  |
|  | Routers: /api/leads | /api/support | /api/invoices | /api/orchestration | /api/... |  |
|  +-----------------------------------------------------------------------------------+  |
|  | Services & Domain Logic:                                                          |  |
|  | - LeadService: Rule Heuristics + OpenAI Structured Qualification Engine           |  |
|  | - SupportService: Intent Classifier + Grounded Knowledge Retrieval (RAG)         |  |
|  | - InvoiceService: PDF Parser + Line-Item Arithmetic Reconciliation Auditor        |  |
|  | - OrchestrationService: Customer Intake + MSA Drafting + Stripe Webhook Verifier  |  |
|  | - WorkflowEngine: Step-by-Step DAG Tracker + Bounded Retries + Approval Queues    |  |
|  | - AgentRegistry: 10 Narrowly-Scoped Autonomous Workforce Persona Definitions      |  |
|  +-----------------------------------------------------------------------------------+  |
|  | Core Subsystems: AuditLogger | EventBroker | ConfigManager (Pydantic Settings)    |  |
+--------------------------------------------+--------------------------------------------+
                                             |
                   +-------------------------+-------------------------+
                   |                                                   |
+------------------v------------------+             +------------------v------------------+
|          Persistence Tier           |             |          Integration Tier           |
| SQLite3 (Thread-Safe WAL Mode)      |             | Modular Adapter Layer with Fallback |
| SQLAlchemy 2.0 ORM & Session Pool   |             | - OpenAI (Live API / Mock LLM)     |
| Tables:                             |             | - Airtable CRM (REST / Mock CRM)    |
| - leads                             |             | - Slack Webhook (Block Kit / Mock)  |
| - support_tickets                   |             | - Email IMAP/SMTP (Draft-Only Mock) |
| - invoices & invoice_items          |             | - Google Sheets (API v4 / Mock CSV) |
| - enterprise_projects & contracts   |             | - Stripe (HMAC SHA-256 Verifier)    |
| - execution_logs                    |             | - n8n & Make.com Webhook Triggers   |
+-------------------------------------+             +-------------------------------------+
```

---

## 2. Core Design Patterns

### 2.1. Modular Integration Adapter Pattern (`integrations/base.py`)
All external service interactions inherit from `BaseIntegrationAdapter`:
- **Circuit Breaker & Status Lifecycle:** Adapters monitor error counts and track five distinct operational states: `demo_mode`, `configured`, `verified_live`, `error`, and `setup_required`.
- **Deterministic Mock Fallback:** When credentials are omitted or invalid, adapters smoothly transition to deterministic mock implementations, ensuring that development and test suites execute without flakiness or external network dependencies.
- **Credential Protection:** Secrets are loaded strictly via server-side environment variables and Pydantic configuration settings; no keys are ever rendered in HTML or sent over client API responses.

### 2.2. Human-in-the-Loop Approval Gates
Critical financial and external dispatches are governed by deterministic approval checkpoints:
- **Customer Support:** Operates in `draft-only` mode by default. Even when an automated response is generated, dispatches cannot be triggered without explicit human review and policy authorization. Sensitive intents (refunds, account deletion, legal disputes) are automatically rerouted to the Escalation Queue.
- **Invoices:** Invoices with mathematical variances or duplicate hashes are blocked from Google Sheets financial export until cleared by an administrator.
- **Contracts:** Generated Master Services Agreements remain in `draft` state and require manual executive approval prior to execution.

### 2.3. Defense-in-Depth AI Guardrails
- **Prompt Injection Neutralization:** Input text from untrusted sources (emails, inbound webhooks) is sanitized, and instruction override delimiters (e.g., `IGNORE PREVIOUS INSTRUCTIONS`) are stripped or neutralized.
- **Structured Schema Enforcement:** AI outputs are validated against strict Pydantic V2 schemas (`response_format={"type": "json_object"}`). In the event of schema failure or malformed JSON, a deterministic heuristic fallback guarantees system continuity.
- **Evidence-Grounded RAG:** Customer support drafting is bound to an approved, localized knowledge base (`data/knowledge_base.json`). If no matching policy is found, the system refrains from inventing answers and triggers human escalation.

---

## 3. Domain Service Architectures

### 3.1. Lead Intelligence Pipeline
```
[Inbound Form / Webhook]
          │
          ▼
   [Validation Engine]  ──(Invalid)──► [HTTP 422 Error / Rejection Audit]
          │ (Valid)
          ▼
   [Normalization]
          │
          ▼
   [Heuristic Pre-Scoring]  (Budget, Company Size, Timeline rules)
          │
          ▼
   [OpenAI Qualification]   (Score 0-100, Priority, Rationale, Talking Points)
          │
          ▼
   [SQLite Persistence]
          │
    ┌─────┴────────────────┐
    ▼                      ▼
[Airtable CRM Upsert]   [Slack Sales Notification]
    │                      │
    └──────────┬───────────┘
               ▼
     [Audit Trail & SLA]
```

### 3.2. Customer Support & Email Intelligence Pipeline
```
[Inbound Email Fixture]
          │
          ▼
   [Header & Body Extraction]
          │
          ▼
   [Prompt Injection Sanitizer]
          │
          ▼
   [Intent & Urgency Classification]
          │
          ▼
   [Knowledge Store Search (RAG)] ──(No Policy Found)──► [Auto-Escalate Queue]
          │ (Relevant Knowledge Retrieved)
          ▼
   [Evidence-Grounded Draft Builder]
          │
          ▼
   [Draft Safety Gate (DRAFT-ONLY)] ──► Stored as Pending Review (Never sent automatically)
```

### 3.3. Invoice Intelligence & Financial Pipeline
```
[PDF Document Upload]
          │
          ▼
   [Header & Size Validation] ──(%PDF- check, max 10MB)
          │
          ▼
   [SHA-256 Hash & Deduplication] ──(Duplicate Found)──► [Flag Duplicate Alert]
          │
          ▼
   [Text / Vision Extraction] (Vendor, Invoice #, Date, Line Items, Tax, Total)
          │
          ▼
   [Arithmetic Reconciliation Audit]
   - Evaluates: Subtotal - Discount + Tax == Total (within $0.05 tolerance)
          │
          ├──(Discrepancy Detected)──► [Flag Warning + Block Export]
          └──(Reconciled)────────────► [Ready for Review]
                                              │
                                              ▼
                                     [Human Approval Gate]
                                              │ (Approved)
                                              ▼
                                     [Google Sheets Export]
```

### 3.4. Enterprise Multi-Agent Orchestration Pipeline
```
[Customer Intake Request]
          │
          ▼
   [Sequential Project Code Allocator] ──► Generates `PRJ-2026-XXX`
          │
          ▼
   [Contract Template Engine] ───────────► Generates Formal MSA Draft
          │
          ▼
   [Stripe Payment Event Ingestion]
          │
          ▼
   [HMAC-SHA256 Signature Verification] ──(Invalid / Replay)──► [Reject & Log Security Alert]
          │ (Verified)
          ▼
   [Slack Collaboration Channel Provisioner] ──► Creates `#prj-2026-xxx-collab`
          │
          ▼
   [Executive Reporting Compiler] ──────────────► Weekly Operations Digest
```

---

## 4. Database Schema Specification

The data tier uses SQLite with Write-Ahead Logging (`WAL` mode) for concurrent read access:

| Table | Primary Key | Key Fields | Purpose |
|---|---|---|---|
| `leads` | `id` (String UUID) | `name`, `email`, `company`, `budget`, `score`, `priority`, `status`, `airtable_record_id`, `slack_ts` | Stores validated and qualified sales prospects |
| `support_tickets` | `id` (String UUID) | `sender`, `subject`, `body`, `intent`, `urgency`, `sentiment`, `draft_response`, `escalated`, `status` | Stores incoming support interactions, classification, and safety-gated drafts |
| `invoices` | `id` (String UUID) | `vendor`, `invoice_number`, `invoice_date`, `subtotal`, `tax_amount`, `total_amount`, `file_hash`, `has_discrepancy`, `is_duplicate`, `is_approved`, `is_exported` | Header records for financial invoices |
| `invoice_items` | `id` (String UUID) | `invoice_id` (FK), `description`, `quantity`, `unit_price`, `amount` | Normalized line items for invoice reconciliation |
| `enterprise_projects`| `id` (String UUID) | `project_code`, `client_name`, `client_email`, `service_tier`, `contract_value`, `contract_status`, `payment_status`, `slack_channel_id` | End-to-end customer onboarding state |
| `execution_logs` | `id` (String UUID) | `event_type`, `action`, `status`, `duration_ms`, `entity_id`, `metadata_json`, `timestamp` | Centralized audit trail and execution telemetry |

---

## 5. Failure Recovery & Circuit Breakers

1. **Transient Network Errors:** When an external API (Airtable, Slack, Google Sheets) fails, the error is recorded in the `execution_logs` table with full stack trace and latency metadata. The affected record is marked with an error badge and queued for retry in the Workflow Studio.
2. **Deterministic Fallbacks:** The platform maintains local mock fixtures so that development, testing, and offline operations are completely decoupled from third-party vendor downtime.
3. **Idempotency Keys:** Duplicate webhook triggers for leads and payments enforce idempotency via unique constraints and SHA-256 signature verification, preventing phantom duplicate record generation.
