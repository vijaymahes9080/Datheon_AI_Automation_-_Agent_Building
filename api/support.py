"""REST API endpoints for Project 2: Customer Support & Email Intelligence."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from core.database import get_db
from core.schemas import SupportEmailIngestRequest, SupportTicketResponse
from services.knowledge_service import KnowledgeService
from services.support_service import SupportService

router = APIRouter(prefix="/api/support", tags=["Support"])
support_service = SupportService()
knowledge_service = KnowledgeService()


class DraftUpdateRequest(BaseModel):
    draft_response: str


class DraftApproveRequest(BaseModel):
    approved_by: str = "Support Lead"


@router.post("/ingest", response_model=dict, status_code=status.HTTP_201_CREATED)
def ingest_support_email(
    payload: SupportEmailIngestRequest,
    db: Session = Depends(get_db),
):
    """Ingest, classify, and generate grounded draft for inbound support email."""
    result = support_service.process_email(payload, db=db)
    ticket = result["ticket"]
    return {
        "success": True,
        "ticket": SupportTicketResponse.from_orm(ticket),
        "duplicate": result.get("duplicate", False),
        "message": result.get("message", "Ticket triaged and draft created safely."),
        "draft_only_enforced": True,
    }


@router.get("/tickets", response_model=List[SupportTicketResponse])
def list_support_tickets(
    intent: Optional[str] = Query(None, description="Filter by intent: BILLING, TECHNICAL_SUPPORT, etc."),
    urgency: Optional[str] = Query(None, description="Filter by urgency: CRITICAL, HIGH, MEDIUM, LOW"),
    status: Optional[str] = Query(None, description="Filter by status: DRAFT_READY, ESCALATED, APPROVED"),
    requires_escalation: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List support tickets in inbox with priority filters."""
    tickets = support_service.get_tickets(
        db, intent=intent, urgency=urgency, status=status, requires_escalation=requires_escalation, limit=limit, offset=offset
    )
    return [SupportTicketResponse.from_orm(t) for t in tickets]


@router.get("/tickets/{ticket_id}", response_model=SupportTicketResponse)
def get_ticket_details(ticket_id: str, db: Session = Depends(get_db)):
    """Retrieve single ticket with complete grounded context."""
    ticket = support_service.get_ticket_by_id(ticket_id, db)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")
    return SupportTicketResponse.from_orm(ticket)


@router.patch("/tickets/{ticket_id}/draft", response_model=SupportTicketResponse)
def update_ticket_draft(
    ticket_id: str,
    payload: DraftUpdateRequest,
    db: Session = Depends(get_db),
):
    """Update and polish draft response before approval."""
    try:
        updated = support_service.update_draft(ticket_id, payload.draft_response, db)
        return SupportTicketResponse.from_orm(updated)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/tickets/{ticket_id}/approve", response_model=dict)
def approve_ticket_draft(
    ticket_id: str,
    payload: DraftApproveRequest,
    db: Session = Depends(get_db),
):
    """Approve draft response (Fulfills human governance gate)."""
    try:
        return support_service.approve_ticket_draft(ticket_id, payload.approved_by, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/knowledge", response_model=List[str])
def search_knowledge_base(query: str = Query(..., min_length=2)):
    """Search approved policy knowledge base."""
    return knowledge_service.search_knowledge(query, top_k=3)


@router.get("/fixtures", response_model=List[dict])
def get_support_fixtures():
    """Retrieve reproducible test fixtures for live demonstration."""
    return support_service.email.get_test_fixtures()
