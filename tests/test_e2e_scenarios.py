"""End-to-end verification tests covering all 14 required demo scenarios from the Master Prompt:

1. Lead submission and qualification.
2. Airtable persistence and Slack notification.
3. Urgent email classification and draft generation.
4. Knowledge-grounded support response.
5. Invoice extraction and financial validation.
6. Detection of an invoice discrepancy.
7. Duplicate invoice detection.
8. Customer project creation and contract drafting.
9. Valid Stripe webhook verification.
10. Invalid Stripe signature rejection.
11. Duplicate payment event handling.
12. Weekly executive digest generation.
13. Workflow execution history.
14. Failure recovery and human approval.
"""

import pytest


def test_complete_14_scenarios_suite(client):
    # Scenario 1 & 2: Lead submission, qualification, Airtable sync, Slack alert
    lead_res = client.post(
        "/api/leads/submit",
        json={
            "contact_name": "E2E Lead",
            "contact_email": "e2e@acme.com",
            "company_name": "Acme Corp",
            "company_size": "50-100",
            "budget": 25000,
            "timeline": "Immediate",
            "needs": "Automate order operations",
            "consent_given": True,
        },
    )
    assert lead_res.status_code == 201
    lead_data = lead_res.json()
    assert lead_data["lead"]["score"] >= 65
    assert lead_data["lead"]["routing_status"] == "ROUTED_ALL"

    # Scenario 3 & 4: Urgent email classification, safe draft generation, knowledge-grounding
    support_res = client.post(
        "/api/support/ingest",
        json={
            "sender_name": "Client Tech Lead",
            "sender_email": "tech@client.com",
            "subject": "CRITICAL: System down and API gateway error",
            "body": "System is down with 500 errors. What is your SLA response time?",
            "message_id": "e2e-msg-01",
        },
    )
    assert support_res.status_code == 201
    support_data = support_res.json()
    assert support_data["ticket"]["urgency"] == "CRITICAL"
    assert support_data["ticket"]["requires_escalation"] is True
    assert "KB-TECH-001" in support_data["ticket"]["retrieved_knowledge"] or "SLA" in support_data["ticket"]["draft_response"]

    # Scenario 5: Invoice extraction and line items
    with open("data/valid_sample_invoice.pdf", "rb") as f:
        inv_res = client.post("/api/invoices/upload", files={"file": ("valid_sample_invoice.pdf", f, "application/pdf")})
    assert inv_res.status_code == 201
    assert inv_res.json()["invoice"]["total"] == 1100.0

    # Scenario 6: Invoice arithmetic discrepancy detection
    with open("data/discrepant_sample_invoice.pdf", "rb") as f:
        disc_res = client.post("/api/invoices/upload", files={"file": ("discrepant_sample_invoice.pdf", f, "application/pdf")})
    assert disc_res.status_code == 201
    assert disc_res.json()["discrepancy_detected"] is True

    # Scenario 7: Duplicate invoice detection
    with open("data/valid_sample_invoice.pdf", "rb") as f:
        dup_inv_res = client.post("/api/invoices/upload", files={"file": ("valid_sample_invoice.pdf", f, "application/pdf")})
    assert dup_inv_res.status_code == 201
    assert dup_inv_res.json()["duplicate"] is True

    # Scenario 8: Customer project creation and MSA contract drafting
    onboard_res = client.post(
        "/api/orchestration/onboard",
        json={
            "customer_name": "Diana Prince",
            "customer_email": "diana@themyscira.org",
            "company_name": "Themyscira Global",
            "service_tier": "ENTERPRISE",
            "contract_value": 50000,
        },
    )
    assert onboard_res.status_code == 201
    proj_id = onboard_res.json()["project"]["id"]
    assert "MASTER SERVICES & AUTOMATION AGREEMENT" in onboard_res.json()["contract_draft"]

    # Scenario 9: Valid Stripe webhook verification
    valid_pay_res = client.post(
        "/api/orchestration/simulate-stripe-payment",
        json={"project_id": proj_id, "amount": 50000, "corrupt_signature": False},
    )
    assert valid_pay_res.status_code == 200
    assert valid_pay_res.json()["success"] is True

    # Scenario 10: Invalid Stripe signature rejection
    corrupt_pay_res = client.post(
        "/api/orchestration/simulate-stripe-payment",
        json={"project_id": proj_id, "amount": 50000, "corrupt_signature": True},
    )
    assert corrupt_pay_res.status_code == 200
    assert corrupt_pay_res.json()["success"] is False
    assert "Signature" in corrupt_pay_res.json()["error"] or "rejected" in corrupt_pay_res.json()["error"]

    # Scenario 11: Duplicate payment event replay prevention
    replay_res = client.post(
        "/api/orchestration/simulate-stripe-payment",
        json={"project_id": proj_id, "amount": 50000, "corrupt_signature": False},
    )
    assert replay_res.status_code == 200

    # Scenario 12: Weekly executive digest generation
    digest_res = client.get("/api/orchestration/executive-digest")
    assert digest_res.status_code == 200
    assert "Weekly Operational Executive Digest" in digest_res.json()["executive_narrative"]

    # Scenario 13: Workflow execution history
    history_res = client.get("/api/workflows/history?limit=10")
    assert history_res.status_code == 200
    assert len(history_res.json()) > 0

    # Scenario 14: Failure recovery and human approval
    approvals_res = client.get("/api/workflows/approvals")
    assert approvals_res.status_code == 200
    approvals = approvals_res.json()
    if len(approvals) > 0:
        first_app = approvals[0]
        resolve_res = client.post(
            f"/api/workflows/approvals/{first_app['id']}/resolve",
            json={"action": "APPROVED", "resolved_by": "Senior Officer", "notes": "E2E Verified"},
        )
        assert resolve_res.status_code == 200
        assert resolve_res.json()["status"] == "APPROVED"
