# Integration Guide & External Service Configuration

This document specifies the setup procedures, permission requirements, authentication protocols, and test verification steps for all external service integrations supported by **ORBIT AI Operations Studio**.

---

## 1. OpenAI Integration

### Overview
Used by **Lead Intelligence** (qualification scoring & talking points), **Customer Support** (intent classification & draft synthesis), and **Invoice Intelligence** (vision extraction fallback).

### Required Credentials & Permissions
- **Account:** OpenAI Platform ([platform.openai.com](https://platform.openai.com))
- **Permission:** Model inference permissions (`gpt-4o-mini`, `gpt-4o`, `text-embedding-3-small`)
- **Environment Variables:**
  ```ini
  OPENAI_ENABLED=true
  OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  OPENAI_MODEL=gpt-4o-mini
  ```

### Structured Output Safeguard
ORBIT requests structured JSON output (`response_format={"type": "json_object"}`) and validates incoming responses against Pydantic models. If the OpenAI API is unreachable or returns malformed data, the system automatically falls back to deterministic heuristic parsing without failing the user's request.

---

## 2. Airtable CRM Integration

### Overview
Used by **Lead Intelligence** and **Enterprise Orchestration** for persistent CRM lead records and customer onboarding tracking.

### Required Credentials & Permissions
- **Account:** Airtable ([airtable.com](https://airtable.com))
- **Personal Access Token (PAT):** Scopes required: `data.records:read`, `data.records:write`, `schema.bases:read`
- **Environment Variables:**
  ```ini
  AIRTABLE_ENABLED=true
  AIRTABLE_API_KEY=patxxxxxxxxxxxxxxxx.xxxxxxxxxxxxxxxx
  AIRTABLE_BASE_ID=appxxxxxxxxxxxxxx
  AIRTABLE_TABLE_NAME=Leads
  ```

### Table Schema Setup
Create a table named `Leads` with the following columns:
- `Name` (Single line text)
- `Email` (Email)
- `Company` (Single line text)
- `Budget` (Number / Currency)
- `Qualification Score` (Number)
- `Priority` (Single select: High, Medium, Low)
- `Talking Points` (Long text)
- `Status` (Single select: New, Qualified, Unqualified)

---

## 3. Slack Collaboration & Notification Integration

### Overview
Used by **Lead Intelligence** (instant high-priority sales alerts) and **Enterprise Orchestration** (provisioning dedicated project channels `#prj-2026-xxx-collab`).

### Required Credentials & Permissions
- **Account:** Slack Workspace ([api.slack.com/apps](https://api.slack.com/apps))
- **Bot Token Scopes:** `chat:write`, `channels:manage`, `channels:read`, `groups:write`, `incoming-webhook`
- **Environment Variables:**
  ```ini
  SLACK_ENABLED=true
  SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx
  SLACK_SALES_CHANNEL=C0123456789
  SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00/B00/XXXXX
  ```

### Block Kit Message Format
Lead alerts are formatted using Slack Block Kit, displaying lead name, score badge, company details, estimated budget, and sales talking points directly in the notification card.

---

## 4. Email Ingestion & Draft-Only Integration

### Overview
Used by **Customer Support & Email Intelligence** to ingest customer emails and prepare context-grounded response drafts.

### Required Credentials & Permissions
- **Account:** Google Workspace / Gmail or Microsoft Outlook / Office 365
- **Credentials:** IMAP and SMTP access with App-Specific Password
- **Environment Variables:**
  ```ini
  EMAIL_ENABLED=true
  EMAIL_IMAP_SERVER=imap.gmail.com
  EMAIL_SMTP_SERVER=smtp.gmail.com
  EMAIL_ACCOUNT=support@yourdomain.com
  EMAIL_PASSWORD=app-specific-password
  EMAIL_DRAFT_ONLY=true
  ```

### Strict Draft-Only Safety Guard
`EMAIL_DRAFT_ONLY=true` is hardcoded as default in `core/config.py`. Generated email responses are placed in the `[Gmail]/Drafts` folder or stored in the database awaiting explicit human sign-off. The application will never automatically dispatch emails without explicit administrative override.

---

## 5. Google Sheets Accounting Export Integration

### Overview
Used by **Invoice Intelligence & Financial Operations** to export approved invoice line items into the corporate general ledger.

### Required Credentials & Permissions
- **Account:** Google Cloud Platform ([console.cloud.google.com](https://console.cloud.google.com))
- **APIs Enabled:** Google Sheets API v4, Google Drive API
- **Credentials:** Service Account JSON Key file
- **Environment Variables:**
  ```ini
  SHEETS_ENABLED=true
  GOOGLE_SERVICE_ACCOUNT_JSON=./credentials/google_service_account.json
  GOOGLE_SPREADSHEET_ID=1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  ```

### Target Spreadsheet Schema
Ensure the target spreadsheet has a worksheet named `Invoices` with headers:
`[Timestamp, Invoice ID, Vendor, Invoice Number, Invoice Date, Subtotal, Tax, Total, Status, Approved By]`

---

## 6. Stripe Payment Webhook Integration

### Overview
Used by **Enterprise Orchestration** to verify customer retainer payments and trigger Slack onboarding automation.

### Required Credentials & Permissions
- **Account:** Stripe Dashboard ([dashboard.stripe.com](https://dashboard.stripe.com))
- **Endpoint URL:** `https://your-domain.com/api/orchestration/stripe/webhook`
- **Events to Listen:** `payment_intent.succeeded`, `checkout.session.completed`
- **Environment Variables:**
  ```ini
  STRIPE_ENABLED=true
  STRIPE_SECRET_KEY=sk_test_51xxxxxxxxxxxxxxxxxxxxxxxx
  STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  ```

### Verification & Replay Protection
The adapter implements raw HMAC-SHA256 signature verification over incoming payloads:
- Rejects requests without `Stripe-Signature` header.
- Extracts `t=<timestamp>` and `v1=<signature>`.
- Rejects payloads older than 300 seconds (5 minutes) to protect against replay attacks.
- Uses `hmac.compare_digest` for constant-time comparison to prevent timing attacks.

---

## 7. Workflow Automation (n8n & Make.com)

Importable blueprints are located in the `workflows/` directory:

1. **`workflows/n8n_lead_routing.json`**:
   - Webhook trigger on `/webhook/lead-intake`
   - Data validation and scoring HTTP call to ORBIT API
   - Airtable row creation node
   - Slack Block Kit alert node
2. **`workflows/n8n_support_triage.json`**:
   - Email trigger (IMAP polling)
   - Classification and RAG query HTTP call to ORBIT API
   - Gmail draft creation node (never send)
   - Escalation branch for urgent/incident tickets
3. **`workflows/n8n_invoice_pipeline.json`**:
   - Google Drive file upload trigger (PDF)
   - OCR and arithmetic audit HTTP call to ORBIT API
   - Human approval trigger (Slack interactive button)
   - Google Sheets append row node
4. **`workflows/make_blueprints.json`**:
   - Equivalent Make.com scenario definitions for enterprise customers utilizing Make.
