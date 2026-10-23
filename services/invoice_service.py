"""Project 3: Invoice Intelligence & Financial Operations Service.

Implements the pipeline:
Upload -> Inspect -> Extract -> Validate -> Reconcile -> Approve -> Export -> Audit
Features mathematical reconciliation, duplicate detection, and Google Sheets export staging.
"""

from datetime import datetime
import hashlib
import io
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from pypdf import PdfReader

from sqlalchemy.orm import Session
from core.audit import timed_execution
from core.models import ApprovalRequest, InvoiceLineItem, InvoiceRecord
from core.schemas import InvoiceExtractResult, InvoiceLineItemSchema
from integrations.sheets_adapter import GoogleSheetsAdapter

logger = logging.getLogger("orbit.services.invoices")


class InvoiceService:
    """Invoice Intelligence and Financial Reconciliation Engine."""

    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

    def __init__(self, sheets_adapter: Optional[GoogleSheetsAdapter] = None):
        self.sheets = sheets_adapter or GoogleSheetsAdapter()

    @staticmethod
    def validate_pdf_bytes(file_bytes: bytes, filename: str) -> None:
        """Enforce strict file size and header validation."""
        if len(file_bytes) == 0:
            raise ValueError("Uploaded file is empty (0 bytes).")
        if len(file_bytes) > InvoiceService.MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File size exceeds maximum allowable limit of 10MB ({len(file_bytes)} bytes).")
        if not file_bytes.startswith(b"%PDF-"):
            raise ValueError(f"File '{filename}' is not a valid PDF document (missing %PDF header signature).")

    @staticmethod
    def compute_sha256(content: bytes) -> str:
        """Compute SHA-256 fingerprint of the document for duplicate detection."""
        return hashlib.sha256(content).hexdigest()

    def extract_text_from_pdf(self, file_bytes: bytes) -> str:
        """Extract textual content from PDF stream using pypdf."""
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            text_parts = []
            for idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
            return "\n".join(text_parts).strip()
        except Exception as err:
            logger.error(f"Failed to parse PDF text: {err}")
            raise ValueError(f"Could not read PDF structure: {str(err)}")

    def parse_invoice_text(self, text: str, filename: str) -> InvoiceExtractResult:
        """Parse structured fields and line items from extracted text using regex & heuristics."""
        # 1. Vendor Extraction
        vendor_match = re.search(r"(?i)vendor[:\s]+([^\n\r]+)", text)
        if vendor_match:
            vendor_name = vendor_match.group(1).strip()
        else:
            first_line = text.split("\n")[0].strip() if text else "Unknown Vendor"
            vendor_name = first_line[:64] if len(first_line) > 3 else "Acme Cloud Services Inc."

        # 2. Invoice Number
        inv_num_match = re.search(r"(?i)invoice\s*(?:#|number|no)?[:\s]*([A-Z0-9\-_]+)", text)
        invoice_number = inv_num_match.group(1).strip() if inv_num_match else f"INV-{int(time.time() * 1000) % 100000}"

        # 3. Invoice Date
        date_match = re.search(r"(?i)date[:\s]*([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        invoice_date = date_match.group(1).strip() if date_match else time.strftime("%Y-%m-%d", time.gmtime())

        # 4. Currency
        currency = "USD"
        if "€" in text or "EUR" in text:
            currency = "EUR"
        elif "£" in text or "GBP" in text:
            currency = "GBP"

        # 5. Stated Payment Status
        stated_status = "UNPAID"
        if re.search(r"(?i)\bPAID\b", text):
            stated_status = "PAID"
        elif re.search(r"(?i)\bPARTIAL\b", text):
            stated_status = "PARTIAL"
        elif re.search(r"(?i)\bDUE\b|\bUNPAID\b|\bPAYMENT REQUIRED\b", text):
            stated_status = "UNPAID"

        # 6. Financial figures extraction
        def extract_amount(pattern: str, default: float = 0.0) -> float:
            m = re.search(pattern, text)
            if m:
                val_str = m.group(1).replace(",", "")
                try:
                    return float(val_str)
                except ValueError:
                    return default
            return default

        subtotal = extract_amount(r"(?i)\bsubtotal[:\s]*\$?([0-9,]+(?:\.[0-9]{2})?)", 0.0)
        tax_amount = extract_amount(r"(?i)\btax[:\s]*\$?([0-9,]+(?:\.[0-9]{2})?)", 0.0)
        discount_amount = extract_amount(r"(?i)\bdiscount[:\s]*\$?([0-9,]+(?:\.[0-9]{2})?)", 0.0)
        total = extract_amount(r"(?i)\btotal[:\s]*\$?([0-9,]+(?:\.[0-9]{2})?)", 0.0)


        # 7. Line Item Extraction (e.g. "Cloud Hosting Tier 1 x $500.00 = $500.00" or tabular rows)
        line_items: List[InvoiceLineItemSchema] = []
        item_patterns = re.findall(
            r"(?i)([A-Za-z0-9\s\-_]{3,40})\s+([0-9]+(?:\.[0-9]+)?)\s+x\s+\$?([0-9,]+\.[0-9]{2})\s*=\s*\$?([0-9,]+\.[0-9]{2})",
            text,
        )
        if item_patterns:
            for item in item_patterns:
                desc = item[0].strip()
                qty = float(item[1])
                price = float(item[2].replace(",", ""))
                ltotal = float(item[3].replace(",", ""))
                line_items.append(
                    InvoiceLineItemSchema(
                        description=desc,
                        quantity=qty,
                        unit_price=price,
                        line_total=ltotal,
                    )
                )

        # If subtotal or total is 0 and line items exist, calculate
        if subtotal == 0.0 and line_items:
            subtotal = sum(li.line_total for li in line_items)
        if total == 0.0 and subtotal > 0.0:
            total = subtotal - discount_amount + tax_amount

        # 8. Arithmetic Discrepancy Reconciliation
        calculated_total = round(subtotal - discount_amount + tax_amount, 2)
        has_discrepancy = False
        discrepancy_details = None

        if abs(calculated_total - round(total, 2)) > 0.05:
            has_discrepancy = True
            diff = round(total - calculated_total, 2)
            discrepancy_details = (
                f"Mathematical discrepancy detected: Stated total (${total:,.2f}) does not match "
                f"calculated total (${calculated_total:,.2f} = Subtotal ${subtotal:,.2f} - Discount ${discount_amount:,.2f} "
                f"+ Tax ${tax_amount:,.2f}). Difference: ${diff:,.2f}."
            )
            logger.warning(f"[InvoiceService] Discrepancy for {invoice_number}: {discrepancy_details}")

        return InvoiceExtractResult(
            vendor_name=vendor_name,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            currency=currency,
            subtotal=subtotal,
            tax_rate=round(tax_amount / max(subtotal, 1.0) * 100, 1) if subtotal > 0 else 0.0,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            total=total,
            stated_payment_status=stated_status,
            line_items=line_items,
            has_arithmetic_discrepancy=has_discrepancy,
            discrepancy_details=discrepancy_details,
        )

    def process_invoice_upload(
        self,
        file_bytes: bytes,
        filename: str,
        db: Session,
    ) -> Dict[str, Any]:
        """Upload, validate, extract, reconcile, and persist invoice record."""
        with timed_execution("invoice_extraction", module="invoices", trigger_type="UPLOAD", db=db) as ctx:
            # 1. Validation & Hash
            self.validate_pdf_bytes(file_bytes, filename)
            file_hash = self.compute_sha256(file_bytes)

            # 2. Duplicate Detection: Check File Hash
            existing_by_hash = db.query(InvoiceRecord).filter(InvoiceRecord.file_hash == file_hash).first()
            if existing_by_hash:
                logger.info(f"Duplicate invoice PDF detected via file hash '{file_hash[:16]}'.")
                ctx["metadata"] = {"duplicate": True, "invoice_id": existing_by_hash.id}
                ctx["related_record_id"] = existing_by_hash.id
                return {
                    "invoice": existing_by_hash,
                    "duplicate": True,
                    "message": f"Duplicate file detected: Identical PDF document already processed ({existing_by_hash.invoice_number}).",
                }

            # 3. Extraction
            extracted_text = self.extract_text_from_pdf(file_bytes)
            parsed: InvoiceExtractResult = self.parse_invoice_text(extracted_text, filename)

            # 4. Duplicate Detection: Check Vendor + Invoice Number
            existing_by_num = (
                db.query(InvoiceRecord)
                .filter(
                    InvoiceRecord.vendor_name == parsed.vendor_name,
                    InvoiceRecord.invoice_number == parsed.invoice_number,
                )
                .first()
            )

            duplicate_detected = bool(existing_by_num)
            duplicate_of_id = existing_by_num.id if existing_by_num else None

            # 5. Determine initial approval status
            # High safety rule: Any discrepancy or duplicate forces human review
            if parsed.has_arithmetic_discrepancy or duplicate_detected:
                approval_status = "PENDING_REVIEW"
            else:
                approval_status = "PENDING_REVIEW"

            # 6. Persistence
            invoice = InvoiceRecord(
                file_name=filename,
                file_hash=file_hash,
                vendor_name=parsed.vendor_name,
                invoice_number=parsed.invoice_number,
                invoice_date=parsed.invoice_date,
                currency=parsed.currency,
                subtotal=parsed.subtotal,
                tax_rate=parsed.tax_rate,
                tax_amount=parsed.tax_amount,
                discount_amount=parsed.discount_amount,
                total=parsed.total,
                stated_payment_status=parsed.stated_payment_status,
                has_arithmetic_discrepancy=parsed.has_arithmetic_discrepancy,
                discrepancy_details=parsed.discrepancy_details,
                duplicate_detected=duplicate_detected,
                duplicate_of_id=duplicate_of_id,
                approval_status=approval_status,
                export_status="NOT_EXPORTED",
            )
            db.add(invoice)
            db.commit()
            db.refresh(invoice)

            ctx["related_record_id"] = invoice.id

            # Save line items
            for item in parsed.line_items:
                li = InvoiceLineItem(
                    invoice_id=invoice.id,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    line_total=item.line_total,
                )
                db.add(li)
            db.commit()

            # Create approval request if discrepancy detected
            if parsed.has_arithmetic_discrepancy or duplicate_detected:
                reason = "Arithmetic discrepancy" if parsed.has_arithmetic_discrepancy else "Duplicate invoice detected"
                app_req = ApprovalRequest(
                    entity_type="INVOICE",
                    entity_id=invoice.id,
                    title=f"Invoice Review: {invoice.vendor_name} ({invoice.invoice_number}) - ${invoice.total:,.2f}",
                    details=f"{reason}: {invoice.discrepancy_details or 'Potential duplicate submission'}",
                    status="PENDING",
                    requested_by="Invoice Intelligence Agent",
                )
                db.add(app_req)
                db.commit()

            ctx["metadata"] = {
                "vendor": invoice.vendor_name,
                "invoice_number": invoice.invoice_number,
                "total": invoice.total,
                "discrepancy": invoice.has_arithmetic_discrepancy,
                "duplicate": duplicate_detected,
            }

            return {
                "invoice": invoice,
                "duplicate": duplicate_detected,
                "extracted_fields": parsed,
                "status": invoice.approval_status,
            }

    def approve_invoice(self, invoice_id: str, approved_by: str, db: Session) -> Dict[str, Any]:
        """Approve invoice for accounting export, satisfying the human review gate."""
        invoice = db.query(InvoiceRecord).filter(InvoiceRecord.id == invoice_id).first()
        if not invoice:
            raise ValueError(f"Invoice '{invoice_id}' not found.")

        invoice.approval_status = "APPROVED"
        invoice.approved_by = approved_by
        invoice.approved_at = datetime.utcnow()
        db.commit()
        db.refresh(invoice)


        logger.info(f"Invoice {invoice.invoice_number} ({invoice.vendor_name}) approved by {approved_by}")
        return {
            "success": True,
            "invoice_id": invoice.id,
            "approval_status": "APPROVED",
            "approved_by": approved_by,
        }

    def export_invoice_to_sheets(self, invoice_id: str, db: Session) -> Dict[str, Any]:
        """Export an approved invoice to Google Sheets."""
        invoice = db.query(InvoiceRecord).filter(InvoiceRecord.id == invoice_id).first()
        if not invoice:
            raise ValueError(f"Invoice '{invoice_id}' not found.")

        if invoice.approval_status != "APPROVED":
            raise PermissionError(
                f"Invoice '{invoice.invoice_number}' cannot be exported: Must be APPROVED by a human reviewer first "
                f"(Current status: {invoice.approval_status})."
            )

        with timed_execution("invoice_sheets_export", module="invoices", trigger_type="MANUAL", db=db) as ctx:
            ctx["related_record_id"] = invoice.id
            try:
                result = self.sheets.append_invoice_row(
                    {
                        "vendor_name": invoice.vendor_name,
                        "invoice_number": invoice.invoice_number,
                        "invoice_date": invoice.invoice_date,
                        "currency": invoice.currency,
                        "subtotal": invoice.subtotal,
                        "tax_amount": invoice.tax_amount,
                        "total": invoice.total,
                        "stated_payment_status": invoice.stated_payment_status,
                        "approved_by": invoice.approved_by or "Finance Lead",
                    }
                )
                invoice.export_status = "EXPORTED_GOOGLE_SHEETS"
                invoice.google_sheets_row_id = result.get("row_id")
                db.commit()
                db.refresh(invoice)
                ctx["metadata"] = result
                return {"success": True, "invoice": invoice, "sheets_result": result}
            except Exception as exc:
                invoice.export_status = "FAILED"
                db.commit()
                logger.error(f"Failed to export invoice {invoice.id} to Google Sheets: {exc}")
                raise

    def get_invoices(
        self,
        db: Session,
        approval_status: Optional[str] = None,
        export_status: Optional[str] = None,
        has_discrepancy: Optional[bool] = None,
        duplicate_detected: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[InvoiceRecord]:
        """Query stored invoices with filtering and pagination."""
        query = db.query(InvoiceRecord)
        if approval_status:
            query = query.filter(InvoiceRecord.approval_status == approval_status.upper())
        if export_status:
            query = query.filter(InvoiceRecord.export_status == export_status.upper())
        if has_discrepancy is not None:
            query = query.filter(InvoiceRecord.has_arithmetic_discrepancy == has_discrepancy)
        if duplicate_detected is not None:
            query = query.filter(InvoiceRecord.duplicate_detected == duplicate_detected)

        return query.order_by(InvoiceRecord.created_at.desc()).offset(offset).limit(limit).all()

    def get_invoice_by_id(self, invoice_id: str, db: Session) -> Optional[InvoiceRecord]:
        """Retrieve single invoice by ID with line items."""
        return db.query(InvoiceRecord).filter(InvoiceRecord.id == invoice_id).first()

