"""Unit and financial safeguards tests for Project 3: Invoice Intelligence."""

import os
import pytest


def test_valid_invoice_extraction(client):
    """Verify clean extraction of valid PDF invoice with mathematical reconciliation."""
    pdf_path = "data/valid_sample_invoice.pdf"
    if not os.path.exists(pdf_path):
        pytest.skip("Test sample PDF not found.")

    with open(pdf_path, "rb") as f:
        res = client.post("/api/invoices/upload", files={"file": ("valid_sample_invoice.pdf", f, "application/pdf")})

    assert res.status_code == 201
    data = res.json()
    assert data["success"] is True
    assert data["discrepancy_detected"] is False
    assert data["invoice"]["subtotal"] == 1000.0
    assert data["invoice"]["total"] == 1100.0


def test_discrepant_invoice_flagged(client):
    """Verify that an invoice with arithmetic error is detected and flagged."""
    pdf_path = "data/discrepant_sample_invoice.pdf"
    if not os.path.exists(pdf_path):
        pytest.skip("Discrepant test sample PDF not found.")

    with open(pdf_path, "rb") as f:
        res = client.post("/api/invoices/upload", files={"file": ("discrepant_sample_invoice.pdf", f, "application/pdf")})

    assert res.status_code == 201
    data = res.json()
    assert data["discrepancy_detected"] is True
    assert "Mathematical discrepancy" in data["discrepancy_details"]


def test_duplicate_invoice_pdf_rejected(client):
    """Verify identical PDF file upload is flagged as duplicate."""
    pdf_path = "data/valid_sample_invoice.pdf"
    if not os.path.exists(pdf_path):
        pytest.skip("Test sample PDF not found.")

    with open(pdf_path, "rb") as f:
        res1 = client.post("/api/invoices/upload", files={"file": ("valid_sample_invoice.pdf", f, "application/pdf")})
    assert res1.status_code == 201

    # Second upload with identical file content
    with open(pdf_path, "rb") as f:
        res2 = client.post("/api/invoices/upload", files={"file": ("valid_sample_invoice.pdf", f, "application/pdf")})
    assert res2.status_code == 201
    assert res2.json()["duplicate"] is True


def test_invoice_export_gate_blocks_unapproved(client):
    """Verify invoices CANNOT be exported to Google Sheets without human approval."""
    pdf_path = "data/valid_sample_invoice.pdf"
    with open(pdf_path, "rb") as f:
        res = client.post("/api/invoices/upload", files={"file": ("valid_sample_invoice.pdf", f, "application/pdf")})
    inv_id = res.json()["invoice"]["id"]

    # Attempt export while status is PENDING_REVIEW
    export_res = client.post(f"/api/invoices/{inv_id}/export")
    assert export_res.status_code == 403
    assert "Must be APPROVED" in export_res.json()["detail"]

    # Now approve invoice
    app_res = client.post(f"/api/invoices/{inv_id}/approve", json={"approved_by": "Finance Lead"})
    assert app_res.status_code == 200

    # Now export succeeds
    export_res2 = client.post(f"/api/invoices/{inv_id}/export")
    assert export_res2.status_code == 200
    assert export_res2.json()["sheets_result"]["success"] is True
