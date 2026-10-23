"""REST API endpoints for Project 3: Invoice Intelligence & Financial Operations."""

from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from core.database import get_db
from core.schemas import InvoiceResponse
from services.invoice_service import InvoiceService

router = APIRouter(prefix="/api/invoices", tags=["Invoices"])
invoice_service = InvoiceService()


class InvoiceApproveRequest(BaseModel):
    approved_by: str = "Finance Operations Lead"


@router.post("/upload", response_model=dict, status_code=status.HTTP_201_CREATED)
async def upload_invoice_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload and process PDF invoice with arithmetic audit and duplicate detection."""
    content = await file.read()
    try:
        result = invoice_service.process_invoice_upload(content, file.filename, db=db)
        inv = result["invoice"]
        return {
            "success": True,
            "invoice": InvoiceResponse.from_orm(inv),
            "duplicate": result.get("duplicate", False),
            "discrepancy_detected": inv.has_arithmetic_discrepancy,
            "discrepancy_details": inv.discrepancy_details,
            "approval_status": inv.approval_status,
        }
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process invoice document: {str(exc)}")


@router.get("", response_model=List[InvoiceResponse])
def list_invoices(
    approval_status: Optional[str] = Query(None, description="PENDING_REVIEW, APPROVED, REJECTED"),
    export_status: Optional[str] = Query(None, description="NOT_EXPORTED, EXPORTED_GOOGLE_SHEETS, FAILED"),
    has_discrepancy: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List processed invoices with status and discrepancy filters."""
    invoices = invoice_service.get_invoices(
        db,
        approval_status=approval_status,
        export_status=export_status,
        has_discrepancy=has_discrepancy,
        limit=limit,
        offset=offset,
    )
    return [InvoiceResponse.from_orm(i) for i in invoices]


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice_details(invoice_id: str, db: Session = Depends(get_db)):
    """Retrieve full invoice details with line items."""
    inv = invoice_service.get_invoice_by_id(invoice_id, db)
    if not inv:
        raise HTTPException(status_code=404, detail=f"Invoice '{invoice_id}' not found.")
    return InvoiceResponse.from_orm(inv)


@router.post("/{invoice_id}/approve", response_model=dict)
def approve_invoice(
    invoice_id: str,
    payload: InvoiceApproveRequest,
    db: Session = Depends(get_db),
):
    """Human approval gate for invoice export."""
    try:
        return invoice_service.approve_invoice(invoice_id, payload.approved_by, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{invoice_id}/export", response_model=dict)
def export_invoice_to_sheets(invoice_id: str, db: Session = Depends(get_db)):
    """Export an approved invoice to Google Sheets."""
    try:
        res = invoice_service.export_invoice_to_sheets(invoice_id, db)
        return {"success": True, "sheets_result": res["sheets_result"]}
    except PermissionError as perm_err:
        raise HTTPException(status_code=403, detail=str(perm_err))
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Google Sheets export failed: {str(exc)}")


@router.get("/sheets/ledger", response_model=List[dict])
def get_sheets_ledger():
    """View staged financial export rows in Google Sheets."""
    return invoice_service.sheets.get_ledger()
