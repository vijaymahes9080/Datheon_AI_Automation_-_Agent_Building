"""REST API endpoints for Project 1: Lead Intelligence & Revenue Routing."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from core.database import get_db
from core.schemas import LeadResponse, LeadSubmissionRequest
from services.lead_service import LeadService

router = APIRouter(prefix="/api/leads", tags=["Leads"])
lead_service = LeadService()


@router.post("/submit", response_model=dict, status_code=status.HTTP_201_CREATED)
def submit_lead_webform(
    payload: LeadSubmissionRequest,
    db: Session = Depends(get_db),
):
    """Lead intake from web forms."""
    result = lead_service.process_lead(payload, db=db, source="web_form")
    lead = result["lead"]
    return {
        "success": True,
        "lead": LeadResponse.from_orm(lead),
        "duplicate": result.get("duplicate", False),
        "message": result.get("message", "Lead processed and routed successfully."),
        "processing_time_ms": lead.processing_time_ms,
    }


@router.post("/webhook", response_model=dict, status_code=status.HTTP_200_OK)
def lead_webhook_endpoint(
    payload: LeadSubmissionRequest,
    db: Session = Depends(get_db),
):
    """External authenticated webhook endpoint for marketing platforms (Make/n8n/Typeform)."""
    result = lead_service.process_lead(payload, db=db, source="webhook")
    lead = result["lead"]
    return {
        "success": True,
        "lead": LeadResponse.from_orm(lead),
        "duplicate": result.get("duplicate", False),
        "routing_status": lead.routing_status,
        "processing_time_ms": lead.processing_time_ms,
    }


@router.get("", response_model=List[LeadResponse])
def list_leads(
    priority: Optional[str] = Query(None, description="Filter by priority: URGENT, HIGH, MEDIUM, LOW"),
    status: Optional[str] = Query(None, description="Filter by status: QUALIFIED, DISQUALIFIED, NEEDS_REVIEW"),
    search: Optional[str] = Query(None, description="Search company, contact, or email"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Retrieve all leads with filtering, search, and pagination."""
    leads = lead_service.get_leads(db, priority=priority, qualification_status=status, search=search, limit=limit, offset=offset)
    return [LeadResponse.from_orm(l) for l in leads]


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead_details(lead_id: str, db: Session = Depends(get_db)):
    """Retrieve single lead details."""
    lead = lead_service.get_lead_by_id(lead_id, db)
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead '{lead_id}' not found.")
    return LeadResponse.from_orm(lead)


@router.post("/{lead_id}/retry", response_model=dict)
def retry_lead_routing(lead_id: str, db: Session = Depends(get_db)):
    """Recover and re-trigger external routing for a lead."""
    try:
        return lead_service.retry_routing(lead_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
