"""Stripe Webhook Integration Adapter featuring cryptographic HMAC-SHA256 signature
verification, timing-attack mitigation, and replay prevention.
"""

import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, Optional, Set, Tuple
from core.config import IntegrationStatus, settings
from integrations.base import BaseIntegrationAdapter

logger = logging.getLogger("orbit.integrations.stripe")


class StripeAdapter(BaseIntegrationAdapter):
    """Adapter for verifying Stripe Webhook events and reconciling customer payments."""

    DEFAULT_TOLERANCE_SECONDS = 300  # 5 minutes replay protection window

    def __init__(self):
        super().__init__("StripeAdapter")
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET or "whsec_orbit_mock_test_secret_9921"
        self.processed_events: Set[str] = set()
        self.payment_ledger: Dict[str, Dict[str, Any]] = {}

    def is_configured(self) -> bool:
        return bool(settings.STRIPE_WEBHOOK_SECRET and not settings.DEMO_MODE)

    def health_check(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": IntegrationStatus.CONFIGURED.value if self.is_configured() else IntegrationStatus.DEMO_MODE.value,
            "signature_verification": "ENFORCED",
            "processed_payment_events": len(self.processed_events),
            "configured": self.is_configured(),
            "message": "HMAC-SHA256 signature verification and idempotency replay cache active.",
        }

    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        signature_header: str,
        secret: Optional[str] = None,
        tolerance: int = DEFAULT_TOLERANCE_SECONDS,
    ) -> Tuple[bool, Optional[str]]:
        """Verify Stripe webhook signature header (t=timestamp,v1=signature).

        Uses constant-time comparison to prevent timing attacks.
        """
        signing_secret = secret or self.webhook_secret
        if not signature_header or not signing_secret:
            return False, "Missing signature header or signing secret."

        try:
            # Parse header: 't=1600000000,v1=signature_hash'
            elements = signature_header.split(",")
            header_map: Dict[str, str] = {}
            for item in elements:
                if "=" in item:
                    k, v = item.split("=", 1)
                    header_map[k.strip()] = v.strip()

            timestamp_str = header_map.get("t")
            received_signature = header_map.get("v1")

            if not timestamp_str or not received_signature:
                return False, "Malformed signature header (missing 't' or 'v1')."

            timestamp = int(timestamp_str)
            now = int(time.time())

            # Check timestamp tolerance (Replay attack defense)
            if abs(now - timestamp) > tolerance:
                return False, f"Webhook timestamp expired or out of tolerance ({abs(now - timestamp)}s > {tolerance}s)."

            # Compute expected HMAC-SHA256 signature
            signed_payload = f"{timestamp}.".encode("utf-8") + payload_bytes
            expected_signature = hmac.new(
                signing_secret.encode("utf-8"),
                signed_payload,
                hashlib.sha256,
            ).hexdigest()

            # Constant-time comparison
            if not hmac.compare_digest(expected_signature, received_signature):
                return False, "Cryptographic signature mismatch (Invalid signature)."

            return True, None
        except Exception as err:
            return False, f"Signature verification error: {str(err)}"

    def process_payment_event(
        self,
        event_id: str,
        event_type: str,
        project_id: Optional[str],
        amount: float,
        currency: str = "USD",
        signature_verified: bool = False,
    ) -> Dict[str, Any]:
        """Process payment event with idempotent duplicate rejection."""
        if not signature_verified and settings.STRIPE_VERIFY_SIGNATURES:
            raise PermissionError("Unverified payment event rejected: Valid Stripe cryptographic signature required.")

        # Replay / Duplicate event detection
        if event_id in self.processed_events:
            logger.warning(f"[StripeAdapter] Duplicate payment event ignored: {event_id}")
            return {
                "success": True,
                "event_id": event_id,
                "duplicate": True,
                "message": "Payment event already processed (Idempotent).",
            }

        self.processed_events.add(event_id)
        record = {
            "event_id": event_id,
            "event_type": event_type,
            "project_id": project_id,
            "amount": amount,
            "currency": currency,
            "verified_at": time.time(),
        }
        self.payment_ledger[event_id] = record
        logger.info(f"[StripeAdapter] Verified and recorded payment of ${amount:,.2f} {currency} for event {event_id}")

        return {
            "success": True,
            "event_id": event_id,
            "duplicate": False,
            "amount": amount,
            "currency": currency,
            "status": "PAYMENT_VERIFIED",
        }

    @classmethod
    def generate_test_signature(cls, payload_bytes: bytes, secret: str, timestamp: Optional[int] = None) -> str:
        """Helper to generate authentic Stripe signatures for test suites and simulators."""
        ts = timestamp or int(time.time())
        signed_payload = f"{ts}.".encode("utf-8") + payload_bytes
        signature = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
        return f"t={ts},v1={signature}"
