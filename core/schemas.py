"""Pydantic V2 schemas for strict payload validation, AI structured output parsing,
and prompt injection defense.
"""

from datetime import datetime
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


def sanitize_untrusted_input(text: str) -> str:
    """Sanitize untrusted text against prompt injection and malicious delimiters."""
    if not text:
        return ""
    # Strip potential delimiter hijack attempts
    sanitized = text.replace("```", "'''")
    # Defend against direct instruction overrides
    patterns = [
        r"(?i)ignore\s+(all\s+)?previous\s+instructions",
        r"(?i)system\s+prompt\s*:",
        r"(?i)you\s+are\s+now\s+in\s+developer\s+mode",
        r"(?i)override\s+all\s+safety\s+checks",
        r"(?i)disregard\s+prior\s+guidelines",
    ]
    for pattern in patterns:
        sanitized = re.sub(pattern, "[FILTERED_INSTRUCTION_OVERRIDE]", sanitized)
    return sanitized.strip()


# ==============================================================================
# PROJECT 1: LEAD SCHEMAS
# ==============================================================================


class LeadSubmissionRequest(BaseModel):
    """External lead intake schema (Web Form / Webhook)."""

    contact_name: str = Field(..., min_length=2, max_length=128)
    contact_email: EmailStr
    company_name: str = Field(..., min_length=2, max_length=128)
    company_size: str = Field(..., max_length=32)
    budget: float = Field(..., ge=0)
    timeline: Optional[str] = Field(default="1-3 months", max_length=64)
    needs: str = Field(..., min_length=5, max_length=2000)
    consent_given: bool = Field(..., description="Must explicitly confirm marketing/contact consent")

    @field_validator("needs", "contact_name", "company_name")
    @classmethod
    def sanitize_strings(cls, v: str) -> str:
        return sanitize_untrusted_input(v)

    @field_validator("consent_given")
    @classmethod
    def require_consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Explicit consent must be provided to submit lead.")
        return v


class LeadQualificationResult(BaseModel):
    """Structured qualification output produced by AI and business rules."""

    score: int = Field(..., ge=0, le=100)
    priority: str = Field(..., pattern="^(URGENT|HIGH|MEDIUM|LOW)$")
    qualification_status: str = Field(..., pattern="^(QUALIFIED|DISQUALIFIED|NEEDS_REVIEW)$")
    rationale: str
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    missing_information: List[str] = Field(default_factory=list)
    sales_talking_points: List[str] = Field(default_factory=list)


class LeadResponse(BaseModel):
    """Lead response model for API."""

    id: str
    idempotency_key: str
    submission_source: str
    contact_name: str
    contact_email: str
    company_name: str
    company_size: str
    budget: float
    timeline: Optional[str]
    needs: str
    score: int
    priority: str
    qualification_status: str
    rationale: Optional[str]
    confidence: float
    missing_information: List[str]
    sales_talking_points: List[str]
    routing_status: str
    airtable_record_id: Optional[str]
    slack_ts: Optional[str]
    processing_time_ms: float
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("missing_information", "sales_talking_points", mode="before")
    @classmethod
    def parse_json_lists(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except Exception:
                return []
        return v or []


# ==============================================================================
# PROJECT 2: SUPPORT SCHEMAS
# ==============================================================================


class SupportEmailIngestRequest(BaseModel):
    """Inbound customer message/email ingestion schema."""

    sender_name: str = Field(..., min_length=2, max_length=128)
    sender_email: EmailStr
    subject: str = Field(..., min_length=1, max_length=256)
    body: str = Field(..., min_length=1, max_length=5000)
    message_id: Optional[str] = None

    @field_validator("body", "subject")
    @classmethod
    def sanitize_body(cls, v: str) -> str:
        return sanitize_untrusted_input(v)


class SupportTriageResult(BaseModel):
    """AI Support classification, grounded draft, and escalation decision."""

    intent: str = Field(
        ...,
        pattern="^(BILLING|TECHNICAL_SUPPORT|ACCOUNT_ACCESS|PRODUCT_ORDER|COMPLAINTS|URGENT_INCIDENTS|SPAM|UNKNOWN)$",
    )
    urgency: str = Field(..., pattern="^(CRITICAL|HIGH|MEDIUM|LOW)$")
    sentiment: str = Field(..., pattern="^(POSITIVE|NEUTRAL|NEGATIVE|ANGRY)$")
    requires_escalation: bool
    escalation_reason: Optional[str] = None
    retrieved_knowledge: List[str] = Field(default_factory=list)
    draft_response: str


class SupportTicketResponse(BaseModel):
    """Support ticket response for inbox UI and API."""

    id: str
    message_id: str
    sender_name: str
    sender_email: str
    subject: str
    clean_body: str
    intent: str
    urgency: str
    sentiment: str
    requires_escalation: bool
    escalation_reason: Optional[str]
    retrieved_knowledge: Optional[str] = None
    draft_response: Optional[str]
    status: str
    is_draft_only: bool
    created_at: datetime

    model_config = {"from_attributes": True}



# ==============================================================================
# PROJECT 3: INVOICE SCHEMAS
# ==============================================================================


class InvoiceLineItemSchema(BaseModel):
    """Single itemized line item in an extracted invoice."""

    description: str
    quantity: float = Field(default=1.0, ge=0)
    unit_price: float = Field(default=0.0, ge=0)
    line_total: float = Field(default=0.0, ge=0)

    model_config = {"from_attributes": True}



class InvoiceExtractResult(BaseModel):
    """Structured extraction of invoice data with arithmetic audit."""

    vendor_name: str
    invoice_number: str
    invoice_date: Optional[str] = None
    currency: str = Field(default="USD", max_length=8)
    subtotal: float = Field(default=0.0, ge=0)
    tax_rate: float = Field(default=0.0, ge=0)
    tax_amount: float = Field(default=0.0, ge=0)
    discount_amount: float = Field(default=0.0, ge=0)
    total: float = Field(..., ge=0)
    stated_payment_status: str = Field(default="UNPAID")
    line_items: List[InvoiceLineItemSchema] = Field(default_factory=list)
    has_arithmetic_discrepancy: bool = False
    discrepancy_details: Optional[str] = None


class InvoiceResponse(BaseModel):
    """Invoice entity response model."""

    id: str
    file_name: str
    file_hash: str
    vendor_name: str
    invoice_number: str
    invoice_date: Optional[str]
    currency: str
    subtotal: float
    tax_rate: float
    tax_amount: float
    discount_amount: float
    total: float
    stated_payment_status: str
    has_arithmetic_discrepancy: bool
    discrepancy_details: Optional[str]
    duplicate_detected: bool
    duplicate_of_id: Optional[str]
    approval_status: str
    approved_by: Optional[str]
    export_status: str
    google_sheets_row_id: Optional[str]
    created_at: datetime
    line_items: List[InvoiceLineItemSchema] = Field(default_factory=list)

    model_config = {"from_attributes": True}



# ==============================================================================
# PROJECT 4: ORCHESTRATION SCHEMAS
# ==============================================================================


class CustomerOnboardRequest(BaseModel):
    """New client onboarding and project intake."""

    customer_name: str = Field(..., min_length=2, max_length=128)
    customer_email: EmailStr
    company_name: str = Field(..., min_length=2, max_length=128)
    service_tier: str = Field(default="ENTERPRISE")
    contract_value: float = Field(..., ge=100)


class StripeWebhookRequest(BaseModel):
    """Incoming Stripe webhook verification wrapper."""

    event_id: str
    event_type: str
    project_id: Optional[str] = None
    amount: float = Field(..., ge=0)
    currency: str = Field(default="USD")
    signature: str


class ExecutiveDigestResponse(BaseModel):
    """Weekly executive operations digest."""

    period: str
    data_freshness: str
    total_leads: int
    qualified_leads: int
    support_workload: int
    urgent_support_cases: int
    invoices_awaiting_review: int
    approved_accounting_exports: int
    verified_payments_total: float
    active_projects: int
    failed_automation_runs: int
    pending_approvals: int
    verified_metrics: Dict[str, Any]
    executive_narrative: str
