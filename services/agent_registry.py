"""Agent Registry defining 10 specialized workforce personas with bounded scopes,
permission boundaries, and operational safety guardrails.
"""

from typing import Any, Dict, List

AGENT_WORKFORCE: List[Dict[str, Any]] = [
    {
        "id": "agent-intake",
        "name": "Intake Agent",
        "role": "Customer & Lead Validation Specialist",
        "status": "ACTIVE",
        "scope": "Ingests incoming web form, webhook, and customer onboarding requests. Enforces input sanitization and deduplication.",
        "layer": "Ingestion & Validation",
        "guardrails": [
            "Sanitizes untrusted input against prompt injections",
            "Computes SHA-256 idempotency keys",
            "Rejects unconsented submissions",
        ],
        "adapters": ["FastAPI Endpoints", "SQLite DB"],
    },
    {
        "id": "agent-lead-intel",
        "name": "Lead Intelligence Agent",
        "role": "Revenue Qualification Specialist",
        "status": "ACTIVE",
        "scope": "Applies business heuristics and LLM evaluation to score leads (0-100), identify missing info, and synthesize sales talking points.",
        "layer": "Intelligence & Evaluation",
        "guardrails": [
            "Deterministic scoring bounds (0-100)",
            "Strict Pydantic V2 schema validation",
            "Explicit flags for missing budget/timelines",
        ],
        "adapters": ["OpenAIAdapter", "AirtableAdapter", "SlackAdapter"],
    },
    {
        "id": "agent-support-triage",
        "name": "Support Triage Agent",
        "role": "Customer Inbound Triage Specialist",
        "status": "ACTIVE",
        "scope": "Classifies message intent across 8 categories, measures urgency and sentiment, and flags sensitive/legal requests.",
        "layer": "Triage & Escalation",
        "guardrails": [
            "Never bypasses mandatory human escalation for refunds or legal threats",
            "Enforces draft-only mode (No automated email dispatches)",
            "Treats email body as untrusted data",
        ],
        "adapters": ["EmailAdapter", "OpenAIAdapter", "SlackAdapter"],
    },
    {
        "id": "agent-knowledge",
        "name": "Knowledge Agent",
        "role": "Evidence Retrieval & Grounding Specialist",
        "status": "ACTIVE",
        "scope": "Performs hybrid vector & keyword retrieval against approved organizational policies.",
        "layer": "RAG & Grounding",
        "guardrails": [
            "Restricted to approved document store",
            "Never hallucinates ungrounded policies",
            "Provides source attribution with Document ID",
        ],
        "adapters": ["KnowledgeService", "Local Policy Store"],
    },
    {
        "id": "agent-invoice",
        "name": "Invoice Agent",
        "role": "Financial Document & OCR Specialist",
        "status": "ACTIVE",
        "scope": "Parses PDF invoices, extracts itemized fields, performs mathematical reconciliation, and detects duplicates.",
        "layer": "Financial Extraction",
        "guardrails": [
            "Reconciles subtotal + tax - discount == total (tolerance $0.05)",
            "Duplicate file SHA-256 fingerprinting",
            "Mandates human approval for any discrepancy",
        ],
        "adapters": ["pypdf Parser", "GoogleSheetsAdapter"],
    },
    {
        "id": "agent-contract",
        "name": "Contract Agent",
        "role": "Template-Governed Legal Drafter",
        "status": "ACTIVE",
        "scope": "Prepares versioned master services agreements using strict template parameters.",
        "layer": "Governance & Legal",
        "guardrails": [
            "Zero dynamic clause generation (Pre-approved templates only)",
            "Requires executive countersignature gate",
            "Assigns immutable project identifiers",
        ],
        "adapters": ["ContractTemplateEngine", "AirtableAdapter"],
    },
    {
        "id": "agent-payment-verification",
        "name": "Payment Verification Service",
        "role": "Deterministic Settlement Guard",
        "status": "ACTIVE",
        "scope": "Validates Stripe webhook cryptographic signatures (HMAC-SHA256) and prevents replay attacks.",
        "layer": "Financial Settlement",
        "guardrails": [
            "Deterministic cryptographic signature verification",
            "Timing attack constant-time comparison",
            "5-minute timestamp tolerance window",
            "Rejects unverified UI conclusions",
        ],
        "adapters": ["StripeAdapter", "PaymentLedger"],
    },
    {
        "id": "agent-collaboration",
        "name": "Collaboration Agent",
        "role": "Team Notifications & Channel Provisioner",
        "status": "ACTIVE",
        "scope": "Creates dedicated project collaboration channels (#prj-...) and dispatches Block Kit operational alerts.",
        "layer": "Operations Collaboration",
        "guardrails": [
            "Idempotent channel creation (prevents duplicates)",
            "Strictly routes alerts to designated channels",
            "No sensitive credentials in channel posts",
        ],
        "adapters": ["SlackAdapter"],
    },
    {
        "id": "agent-executive-reporting",
        "name": "Executive Reporting Agent",
        "role": "Operational Digest & Telemetry Synthesizer",
        "status": "ACTIVE",
        "scope": "Compiles weekly executive digests grounded strictly in stored system metrics and error audits.",
        "layer": "Executive Intelligence",
        "guardrails": [
            "Distinguishes verified metrics from generated narrative",
            "Includes data freshness timestamp and reporting window",
            "Direct citations of stored database counts",
        ],
        "adapters": ["AuditEngine", "OpenAIAdapter"],
    },
    {
        "id": "agent-supervisor",
        "name": "Workflow Supervisor",
        "role": "System Orchestrator & Approval Sentinel",
        "status": "ACTIVE",
        "scope": "Monitors end-to-end execution latency, manages bounded retry queues, and enforces human-in-the-loop approval gates.",
        "layer": "Supervision & Governance",
        "guardrails": [
            "Bounded exponential backoff retries",
            "Enforces approval gates before irreversible actions",
            "Records persistent execution audit trail",
        ],
        "adapters": ["WorkflowEngine", "ApprovalCenter"],
    },
]


def get_agent_registry() -> List[Dict[str, Any]]:
    """Return complete agent registry."""
    return AGENT_WORKFORCE


def get_agent_by_id(agent_id: str) -> Dict[str, Any]:
    """Retrieve specific agent metadata."""
    for agent in AGENT_WORKFORCE:
        if agent["id"] == agent_id:
            return agent
    raise ValueError(f"Agent '{agent_id}' not found in registry.")
