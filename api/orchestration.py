"""REST API endpoints for Project 4: Enterprise Multi-Agent Business Orchestration."""

import json
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from core.database import get_db
from core.schemas import CustomerOnboardRequest, ExecutiveDigestResponse
from integrations.stripe_adapter import StripeAdapter
from services.orchestration_service import OrchestrationService

router = APIRouter(prefix="/api/orchestration", tags=["Enterprise Orchestration"])
orchestration_service = OrchestrationService()


class ContractApproveRequest(BaseModel):
    approved_by: str = "Chief Commercial Officer"


class SimulatePaymentRequest(BaseModel):
    project_id: str
    amount: float
    currency: str = "USD"
    corrupt_signature: bool = False


@router.post("/onboard", response_model=dict, status_code=status.HTTP_201_CREATED)
def onboard_customer(
    payload: CustomerOnboardRequest,
    db: Session = Depends(get_db),
):
    """Customer intake, stable project code allocation, and contract draft generation."""
    res = orchestration_service.onboard_customer(payload, db=db)
    proj = res["project"]
    return {
        "success": True,
        "project": {
            "id": proj.id,
            "project_code": proj.project_code,
            "customer_name": proj.customer_name,
            "company_name": proj.company_name,
            "service_tier": proj.service_tier,
            "contract_value": proj.contract_value,
            "contract_status": proj.contract_status,
            "workflow_state": proj.workflow_state,
        },
        "duplicate": res.get("duplicate", False),
        "contract_draft": res.get("contract_draft"),
    }


@router.get("/projects", response_model=List[dict])
def list_projects(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List customer projects and onboarding statuses."""
    projects = orchestration_service.get_projects(db, limit=limit, offset=offset)
    return [
        {
            "id": p.id,
            "project_code": p.project_code,
            "customer_name": p.customer_name,
            "company_name": p.company_name,
            "service_tier": p.service_tier,
            "contract_value": p.contract_value,
            "contract_status": p.contract_status,
            "payment_status": p.payment_status,
            "workflow_state": p.workflow_state,
            "slack_channel": p.slack_channel_name,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in projects
    ]


@router.get("/projects/{project_id}", response_model=dict)
def get_project_details(project_id: str, db: Session = Depends(get_db)):
    """Retrieve full project details and contract draft."""
    proj = orchestration_service.get_project_by_id(project_id, db)
    if not proj:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    return {
        "id": proj.id,
        "project_code": proj.project_code,
        "customer_name": proj.customer_name,
        "customer_email": proj.customer_email,
        "company_name": proj.company_name,
        "service_tier": proj.service_tier,
        "contract_value": proj.contract_value,
        "contract_status": proj.contract_status,
        "contract_approved_by": proj.contract_approved_by,
        "contract_content": proj.contract_content,
        "payment_status": proj.payment_status,
        "slack_channel_name": proj.slack_channel_name,
        "workflow_state": proj.workflow_state,
        "created_at": proj.created_at.isoformat() if proj.created_at else None,
    }


@router.post("/projects/{project_id}/approve-contract", response_model=dict)
def approve_contract(
    project_id: str,
    payload: ContractApproveRequest,
    db: Session = Depends(get_db),
):
    """Approve contract draft, provision Slack channel, and unlock payment."""
    try:
        return orchestration_service.approve_contract(project_id, payload.approved_by, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/stripe-webhook", response_model=dict)
async def stripe_webhook_endpoint(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    """Official Stripe webhook handler with cryptographic HMAC-SHA256 signature verification."""
    payload_bytes = await request.body()
    try:
        data = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed JSON webhook body.")

    event_id = data.get("id") or f"evt_{int(time.time() * 1000)}"
    event_type = data.get("type", "payment_intent.succeeded")
    project_id = data.get("data", {}).get("object", {}).get("metadata", {}).get("project_id")
    amount = float(data.get("data", {}).get("object", {}).get("amount", 0)) / 100.0  # Stripe amounts in cents
    currency = data.get("data", {}).get("object", {}).get("currency", "USD").upper()

    try:
        result = orchestration_service.verify_stripe_payment(
            event_id=event_id,
            event_type=event_type,
            raw_payload_bytes=payload_bytes,
            signature_header=stripe_signature or "",
            project_id=project_id,
            amount=amount,
            currency=currency,
            db=db,
        )
        return result
    except PermissionError as p_err:
        raise HTTPException(status_code=400, detail=str(p_err))


@router.post("/simulate-stripe-payment", response_model=dict)
def simulate_stripe_payment(
    payload: SimulatePaymentRequest,
    db: Session = Depends(get_db),
):
    """Demonstration & testing helper: Generates authentic signed Stripe webhook payload."""
    import time

    event_id = f"evt_sim_{int(time.time() * 1000)}"
    body_dict = {
        "id": event_id,
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": f"pi_{int(time.time() * 1000)}",
                "amount": int(payload.amount * 100),
                "currency": payload.currency.lower(),
                "metadata": {"project_id": payload.project_id},
            }
        },
    }
    raw_bytes = json.dumps(body_dict).encode("utf-8")
    secret = orchestration_service.stripe.webhook_secret

    if payload.corrupt_signature:
        sig_header = "t=1600000000,v1=corrupted_invalid_signature_hash_0000"
    else:
        sig_header = StripeAdapter.generate_test_signature(raw_bytes, secret)

    try:
        result = orchestration_service.verify_stripe_payment(
            event_id=event_id,
            event_type="payment_intent.succeeded",
            raw_payload_bytes=raw_bytes,
            signature_header=sig_header,
            project_id=payload.project_id,
            amount=payload.amount,
            currency=payload.currency,
            db=db,
        )
        return {
            "success": True,
            "result": result,
            "signature_used": sig_header,
            "corrupt_signature_tested": payload.corrupt_signature,
        }
    except PermissionError as perm_err:
        return {
            "success": False,
            "error": str(perm_err),
            "signature_used": sig_header,
            "corrupt_signature_tested": payload.corrupt_signature,
        }


@router.get("/executive-digest", response_model=ExecutiveDigestResponse)
def get_executive_digest(db: Session = Depends(get_db)):
    """Generate weekly executive operations digest grounded strictly in stored records."""
    return orchestration_service.generate_weekly_executive_digest(db)


@router.get("/payments", response_model=List[dict])
def list_payments(db: Session = Depends(get_db)):
    """List verified Stripe payment events."""
    events = orchestration_service.get_payment_events(db)
    return [
        {
            "id": e.id,
            "event_id": e.stripe_event_id,
            "event_type": e.event_type,
            "project_id": e.project_id,
            "amount": e.amount,
            "currency": e.currency,
            "signature_verified": e.signature_verified,
            "processed_at": e.processed_at.isoformat() if e.processed_at else None,
        }
        for e in events
    ]
