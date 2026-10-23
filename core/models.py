"""SQLAlchemy 2.0 ORM data models for all four business modules,
workflow execution logs, and approval centers.
"""

from datetime import datetime
import uuid
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from core.database import Base


def generate_uuid() -> str:
    """Generate a unique hex string for primary keys."""
    return uuid.uuid4().hex


class LeadRecord(Base):
    """Project 1: Lead Intelligence and Revenue Routing entity."""

    __tablename__ = "leads"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    idempotency_key = Column(String(128), unique=True, index=True, nullable=False)
    submission_source = Column(String(32), default="web_form")  # web_form, webhook, api

    # Contact details
    contact_name = Column(String(128), nullable=False)
    contact_email = Column(String(128), nullable=False, index=True)
    company_name = Column(String(128), nullable=False)
    company_size = Column(String(32), nullable=False)
    budget = Column(Float, nullable=False)
    timeline = Column(String(64), nullable=True)
    needs = Column(Text, nullable=False)
    consent_given = Column(Boolean, default=True)

    # Qualification & AI evaluation
    score = Column(Integer, default=0)
    priority = Column(String(16), default="MEDIUM")  # URGENT, HIGH, MEDIUM, LOW
    qualification_status = Column(String(32), default="NEEDS_REVIEW")  # QUALIFIED, DISQUALIFIED, NEEDS_REVIEW
    rationale = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0)
    missing_information = Column(Text, nullable=True)  # JSON-encoded list
    sales_talking_points = Column(Text, nullable=True)  # JSON-encoded list

    # Routing and External Sync
    routing_status = Column(String(32), default="PENDING")  # PENDING, ROUTED_ALL, FAILED, PARTIAL
    airtable_record_id = Column(String(64), nullable=True)
    slack_ts = Column(String(64), nullable=True)
    processing_time_ms = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SupportTicket(Base):
    """Project 2: Customer Support and Email Intelligence entity."""

    __tablename__ = "support_tickets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    message_id = Column(String(128), unique=True, index=True, nullable=False)

    sender_name = Column(String(128), nullable=False)
    sender_email = Column(String(128), nullable=False, index=True)
    subject = Column(String(256), nullable=False)
    raw_body = Column(Text, nullable=False)
    clean_body = Column(Text, nullable=False)

    # Intelligence & Classification
    intent = Column(String(32), default="UNKNOWN")  # BILLING, TECHNICAL_SUPPORT, etc.
    urgency = Column(String(16), default="MEDIUM")  # CRITICAL, HIGH, MEDIUM, LOW
    sentiment = Column(String(16), default="NEUTRAL")  # POSITIVE, NEUTRAL, NEGATIVE, ANGRY

    requires_escalation = Column(Boolean, default=False)
    escalation_reason = Column(Text, nullable=True)
    retrieved_knowledge = Column(Text, nullable=True)  # Grounded reference snippets
    draft_response = Column(Text, nullable=True)

    status = Column(String(32), default="DRAFT_READY")  # RECEIVED, DRAFT_READY, ESCALATED, APPROVED, CLOSED
    is_draft_only = Column(Boolean, default=True)
    sent_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InvoiceRecord(Base):
    """Project 3: Invoice Intelligence and Financial Operations entity."""

    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    file_name = Column(String(256), nullable=False)
    file_hash = Column(String(64), unique=True, index=True, nullable=False)  # SHA-256 for duplicate detection

    vendor_name = Column(String(128), nullable=False)
    invoice_number = Column(String(64), nullable=False, index=True)
    invoice_date = Column(String(32), nullable=True)
    currency = Column(String(8), default="USD")

    # Financial arithmetic
    subtotal = Column(Float, default=0.0)
    tax_rate = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    stated_payment_status = Column(String(32), default="UNPAID")  # PAID, UNPAID, PARTIAL, UNKNOWN

    has_arithmetic_discrepancy = Column(Boolean, default=False)
    discrepancy_details = Column(Text, nullable=True)
    duplicate_detected = Column(Boolean, default=False)
    duplicate_of_id = Column(String(36), nullable=True)

    approval_status = Column(String(32), default="PENDING_REVIEW")  # PENDING_REVIEW, APPROVED, REJECTED
    approved_by = Column(String(64), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    export_status = Column(String(32), default="NOT_EXPORTED")  # NOT_EXPORTED, EXPORTED_GOOGLE_SHEETS, FAILED
    google_sheets_row_id = Column(String(64), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    line_items = relationship("InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLineItem(Base):
    """Individual line items within an extracted invoice."""

    __tablename__ = "invoice_line_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=False)

    description = Column(String(256), nullable=False)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, default=0.0)
    line_total = Column(Float, default=0.0)

    invoice = relationship("InvoiceRecord", back_populates="line_items")


class CustomerProject(Base):
    """Project 4: Multi-Agent Client Onboarding and Project Orchestration entity."""

    __tablename__ = "customer_projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_code = Column(String(32), unique=True, index=True, nullable=False)  # Stable ID e.g. "PRJ-2026-001"

    customer_name = Column(String(128), nullable=False)
    customer_email = Column(String(128), nullable=False)
    company_name = Column(String(128), nullable=False)
    service_tier = Column(String(64), default="ENTERPRISE")
    contract_value = Column(Float, default=0.0)

    # Contract preparation & legal safety
    contract_template_version = Column(String(32), default="v3.1-standard")
    contract_status = Column(String(32), default="DRAFT")  # DRAFT, PENDING_APPROVAL, APPROVED, SIGNED
    contract_content = Column(Text, nullable=True)
    contract_approved_by = Column(String(64), nullable=True)

    # Integration coordinates
    airtable_project_id = Column(String(64), nullable=True)
    slack_channel_id = Column(String(64), nullable=True)
    slack_channel_name = Column(String(64), nullable=True)

    # Stripe verification
    stripe_customer_id = Column(String(64), nullable=True)
    stripe_payment_intent_id = Column(String(64), nullable=True)
    payment_status = Column(String(32), default="UNPAID")  # UNPAID, VERIFIED, REFUNDED

    workflow_state = Column(String(32), default="INTAKE")  # INTAKE, CONTRACT_PENDING, PAYMENT_PENDING, ONBOARDED

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaymentEvent(Base):
    """Deterministic, auditable Stripe webhook payment events."""

    __tablename__ = "payment_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    stripe_event_id = Column(String(128), unique=True, index=True, nullable=False)  # For replay attack prevention
    event_type = Column(String(64), nullable=False)
    project_id = Column(String(36), nullable=True)

    amount = Column(Float, default=0.0)
    currency = Column(String(8), default="USD")
    signature_verified = Column(Boolean, default=False)
    processed_at = Column(DateTime, default=datetime.utcnow)
    raw_payload = Column(Text, nullable=True)


class ExecutionAuditLog(Base):
    """Traceable execution telemetry and latency ledger for all system workflows."""

    __tablename__ = "execution_audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_name = Column(String(64), index=True, nullable=False)
    module = Column(String(32), index=True, nullable=False)
    trigger_type = Column(String(32), default="API")  # WEBHOOK, MANUAL, CRON, API
    status = Column(String(32), default="SUCCESS")  # SUCCESS, FAILED, RETRYING, REQUIRES_APPROVAL
    duration_ms = Column(Float, default=0.0)
    related_record_id = Column(String(64), nullable=True)
    details = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ApprovalRequest(Base):
    """Human-in-the-loop governance for high-consequence operations."""

    __tablename__ = "approval_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_type = Column(String(32), nullable=False)  # INVOICE, CONTRACT, SUPPORT_ESCALATION, WORKFLOW_RETRY
    entity_id = Column(String(64), nullable=False)
    title = Column(String(256), nullable=False)
    details = Column(Text, nullable=True)
    status = Column(String(32), default="PENDING")  # PENDING, APPROVED, REJECTED
    requested_by = Column(String(64), default="System Supervisor")
    resolved_by = Column(String(64), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
