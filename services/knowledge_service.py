"""Approved Knowledge Retrieval Engine (RAG) for Customer Support.

Guarantees evidence-grounded answers strictly from authorized operational policies.
Never invents answers absent from the approved knowledge base.
"""

import json
import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("orbit.services.knowledge")


DEFAULT_APPROVED_POLICIES: List[Dict[str, Any]] = [
    {
        "id": "KB-BILL-001",
        "title": "API Overage Billing & Calculations",
        "category": "BILLING",
        "keywords": ["overage", "charge", "calculation", "units", "allowance", "plan discount", "invoice"],
        "content": (
            "API overages are billed at $0.05 per 1,000 requests beyond the included 100,000 base monthly units. "
            "Plan discounts (e.g. Agency 20% discount) apply exclusively to the base recurring platform subscription, "
            "not to variable infrastructure overages. Customers can view exact per-day usage in the Usage tab."
        ),
    },
    {
        "id": "KB-BILL-002",
        "title": "Annual Renewal & Refund Policy",
        "category": "BILLING",
        "keywords": ["refund", "annual renewal", "cancel", "money back", "billing dispute", "auto-renew"],
        "content": (
            "Annual subscription renewals are eligible for a full refund within 14 calendar days of billing, provided "
            "that API utilization during the renewed cycle does not exceed 5% of monthly allocation. All refund and credit "
            "authorizations require approval by the Senior Finance Operations team and cannot be dispatched automatically."
        ),
    },
    {
        "id": "KB-TECH-001",
        "title": "Production Incidents & High-Severity SLA",
        "category": "URGENT_INCIDENTS",
        "keywords": ["outage", "down", "critical", "500", "gateway timeout", "timeout", "emergency", "incident"],
        "content": (
            "Production severity 1 incidents (gateway outage, total service failure) trigger high-priority alerts to on-call "
            "infrastructure engineering. Guaranteed SLA acknowledgment is within 15 minutes. Real-time incident telemetry "
            "is published to status.orbit-ai.com."
        ),
    },
    {
        "id": "KB-ACC-001",
        "title": "Two-Factor Authentication (2FA) Reset Workflow",
        "category": "ACCOUNT_ACCESS",
        "keywords": ["2fa", "two-factor", "authenticator", "lost phone", "reset password", "backup key", "locked out"],
        "content": (
            "To reset two-factor authentication when a device is lost, the account owner must provide an unhashed backup code "
            "or complete an authorized video identity challenge. Support agents cannot bypass 2FA via plain email requests "
            "due to SOC-2 Type II security requirements."
        ),
    },
    {
        "id": "KB-PRIV-001",
        "title": "GDPR and Account Deletion Protocol",
        "category": "COMPLAINTS",
        "keywords": ["delete account", "gdpr", "data deletion", "privacy", "right to be forgotten"],
        "content": (
            "GDPR erasure and account termination requests require formal escalation to the Data Protection Officer (DPO). "
            "Data is purged within 30 days following cryptographic signature verification of the account holder's identity."
        ),
    },
    {
        "id": "KB-PROD-001",
        "title": "Webhook Retries and Delivery Guarantees",
        "category": "TECHNICAL_SUPPORT",
        "keywords": ["webhook", "retry", "failure", "idempotency", "event delivery", "latency"],
        "content": (
            "Webhooks are dispatched with exponential backoff retries at 1m, 5m, 15m, and 1h intervals. "
            "Webhook payloads include an 'idempotency-key' header; receiver endpoints must return HTTP 200 within 5,000ms."
        ),
    },
]


class KnowledgeService:
    """Retrieval service for grounded support answers."""

    def __init__(self, policies: Optional[List[Dict[str, Any]]] = None):
        self.documents = policies or DEFAULT_APPROVED_POLICIES

    def search_knowledge(self, query: str, top_k: int = 2) -> List[str]:
        """Perform semantic & keyword search across approved knowledge articles."""
        if not query.strip():
            return []

        tokens = set(re.findall(r"\w+", query.lower()))
        scored_docs: List[Tuple[float, str]] = []

        for doc in self.documents:
            score = 0.0
            # Keyword score
            for kw in doc.get("keywords", []):
                if kw in query.lower():
                    score += 3.0
            # Word overlap with title & content
            doc_tokens = set(re.findall(r"\w+", (doc["title"] + " " + doc["content"]).lower()))
            overlap = len(tokens.intersection(doc_tokens))
            score += overlap * 0.5

            if score > 0:
                snippet = f"[{doc['id']} - {doc['title']}]: {doc['content']}"
                scored_docs.append((score, snippet))

        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc[1] for doc in scored_docs[:top_k]]
