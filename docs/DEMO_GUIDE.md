# Demonstration Guide: 14 Verifiable Demo Scenarios

This guide provides reproducible, step-by-step instructions for demonstrating all 14 mandatory business automation scenarios in **ORBIT AI Operations Studio**.

You can execute these demonstrations either using the **Interactive Web Studio** at `http://127.0.0.1:8000` or via direct **cURL / API requests**.

---

## Scenario 1: Lead Submission & Automated Qualification

### Objective
Demonstrate lead capture from an inbound web form, automated data validation, heuristic + AI scoring, priority assignment, and sales talking-point synthesis.

### Web UI Steps
1. Navigate to **Lead Intelligence** in the left sidebar.
2. In the **Lead Intake Form**, input:
   - **Name:** `Elena Rostova`
   - **Email:** `elena@apexlogistics.com`
   - **Company:** `Apex Global Logistics`
   - **Budget ($):** `35000`
   - **Timeline:** `immediate`
   - **Needs:** `Automate multi-carrier shipping rate comparison and warehouse fulfillment workflows.`
3. Click **Submit & Qualify Lead**.
4. Observe the instant qualification card: Score `85/100`, Priority `HIGH`, with synthesized sales talking points.

### Direct API cURL
```bash
curl -X POST http://127.0.0.1:8000/api/leads/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Elena Rostova",
    "email": "elena@apexlogistics.com",
    "company": "Apex Global Logistics",
    "budget": 35000,
    "timeline": "immediate",
    "needs_description": "Automate multi-carrier shipping rate comparison and warehouse fulfillment workflows.",
    "consent": true
  }'
```

---

## Scenario 2: Airtable Persistence & Slack Notification

### Objective
Verify that the qualified lead is persisted to the Airtable CRM adapter and dispatches a Slack Block Kit alert (or verified mock outcome).

### Verification Steps
1. In the Lead profile card, observe the **Integration Status**:
   - `Airtable Record ID: rec_mock_...`
   - `Slack TS: 1729648900.123400`
2. Open the **Execution History** page:
   - Verify an audit entry for `lead.qualification.completed` and `lead.notification.dispatched` with sub-100ms latency.

---

## Scenario 3: Urgent Support Email Classification & Draft

### Objective
Demonstrate inbound email classification, sentiment analysis, urgency detection, and draft response creation.

### Web UI Steps
1. Navigate to **Support Intelligence**.
2. Click **Simulate Inbound Email** and enter:
   - **Sender:** `ops-lead@enterprise-client.com`
   - **Subject:** `CRITICAL: Payment gateway down on EU store`
   - **Body:** `Our European checkout is throwing 500 errors on all Stripe transactions. Customers cannot pay! Fix this immediately!`
3. Click **Ingest & Triage**.
4. Observe classification: Intent `urgent_incident`, Urgency `CRITICAL`, Status `Escalated`.

---

## Scenario 4: Knowledge-Grounded Support Response (RAG)

### Objective
Verify that support drafts cite approved operational knowledge without fabricating answers.

### Web UI Steps
1. In Support Intelligence, simulate:
   - **Subject:** `What is your refund policy for annual subscriptions?`
   - **Body:** `Can I get a refund if I cancel 15 days into my annual contract?`
2. Click **Ingest & Triage**.
3. View the generated draft: It directly cites the 30-day money-back guarantee policy from `data/knowledge_base.json` and flags that refunds require managerial approval.

---

## Scenario 5: Invoice Extraction & Financial Validation

### Objective
Extract structured invoice data from a valid PDF and verify line items and arithmetic reconciliation.

### Web UI Steps
1. Navigate to **Invoice Intelligence**.
2. Upload `data/valid_sample_invoice.pdf`.
3. Click **Inspect & Reconcile**.
4. Observe extracted fields:
   - Vendor: `CloudScale Infrastructure Services`
   - Subtotal: `$1,250.00`, Tax: `$125.00`, Total: `$1,375.00`
   - Status: `RECONCILED - No Discrepancies Found`.

---

## Scenario 6: Detection of an Invoice Discrepancy

### Objective
Demonstrate mathematical validation safeguards detecting a calculation discrepancy and blocking export.

### Web UI Steps
1. In Invoice Intelligence, upload `data/discrepant_sample_invoice.pdf`.
2. Click **Inspect & Reconcile**.
3. Observe the prominent red banner:
   - `WARNING: Arithmetic Discrepancy Detected!`
   - Line items + tax do not match stated total (Variance: `$110.00`).
   - Export button is locked until manual review approval.

---

## Scenario 7: Duplicate Invoice Detection

### Objective
Prevent duplicate supplier billing using cryptographic file hashing.

### Web UI Steps
1. In Invoice Intelligence, upload `data/valid_sample_invoice.pdf` a second time.
2. Click **Inspect & Reconcile**.
3. Observe the alert:
   - `DUPLICATE INVOICE: An identical file hash (SHA-256) has already been processed.`

---

## Scenario 8: Customer Project Creation & Contract Drafting

### Objective
Coordinate enterprise client onboarding with automated project ID allocation and template-based contract drafting.

### Web UI Steps
1. Navigate to **Enterprise Orchestration**.
2. In **Client Onboarding**, input:
   - **Client Name:** `David Sterling`
   - **Email:** `david@sterlinggrowth.com`
   - **Company:** `Sterling Growth Partners`
   - **Service Tier:** `Enterprise AI Workforce`
   - **Contract Value ($):** `75000`
3. Click **Initiate Onboarding**.
4. Verify assigned Project ID (`PRJ-2026-001`) and generated Master Services Agreement draft.

---

## Scenario 9: Valid Stripe Webhook Verification

### Objective
Verify that a cryptographically signed Stripe payment event transitions project state to `Paid`.

### Direct API cURL
```bash
curl -X POST http://127.0.0.1:8000/api/orchestration/stripe/webhook \
  -H "Content-Type: application/json" \
  -H "Stripe-Signature: t=1729648800,v1=valid_mock_signature" \
  -d '{
    "type": "payment_intent.succeeded",
    "data": {
      "object": {
        "id": "pi_3MtwBwLkdIwHu7ix28a3tqPa",
        "amount": 7500000,
        "currency": "usd",
        "metadata": {"project_id": "PRJ-2026-001"}
      }
    }
  }'
```

---

## Scenario 10: Invalid Stripe Signature Rejection

### Objective
Verify that spoofed or unsigned Stripe webhooks are rejected with HTTP 400/401 and logged.

### Direct API cURL
```bash
curl -X POST http://127.0.0.1:8000/api/orchestration/stripe/webhook \
  -H "Content-Type: application/json" \
  -H "Stripe-Signature: t=1729648800,v1=corrupted_invalid_signature" \
  -d '{"type": "payment_intent.succeeded"}'
```
**Expected Response:** HTTP 400 Bad Request (`Invalid Stripe signature or HMAC verification failure`).

---

## Scenario 11: Duplicate Payment Event Handling

### Objective
Ensure replay or duplicate Stripe webhooks do not double-bill or duplicate onboarding channels.

### Verification Steps
1. Dispatch the identical payload from Scenario 9 a second time.
2. The endpoint returns `200 OK` with status `duplicate_ignored`, preserving idempotency.

---

## Scenario 12: Weekly Executive Digest Generation

### Objective
Compile an executive operations report based strictly on stored database metrics.

### Web UI Steps
1. In Enterprise Orchestration, scroll to **Weekly Executive Digest**.
2. Click **Generate Fresh Digest**.
3. Inspect verified metrics:
   - Qualified Leads, Pending Invoices, Reconciled Financials, Escalated Tickets.

---

## Scenario 13: Workflow Execution History & Telemetry

### Objective
Review granular execution traces with millisecond durations, timestamps, and error logs.

### Web UI Steps
1. Navigate to **Execution History**.
2. View the chronological audit table showing event types, status badges, and duration metrics.

---

## Scenario 14: Failure Recovery & Human Approval

### Objective
Demonstrate human-in-the-loop sign-off for flagged items.

### Web UI Steps
1. Navigate to **Approval Center**.
2. Locate the flagged invoice or contract draft from Scenarios 6 & 8.
3. Review audit rationale and click **Approve Record**.
4. The record is cleared and now eligible for export.
