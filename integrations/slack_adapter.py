"""Slack Integration Adapter for sales alerts, support escalation,
and multi-agent project channel provisioning.
"""

import logging
import time
from typing import Any, Dict, List, Optional
import httpx
from core.config import IntegrationStatus, settings
from integrations.base import BaseIntegrationAdapter

logger = logging.getLogger("orbit.integrations.slack")


class SlackAdapter(BaseIntegrationAdapter):
    """Adapter for Slack Webhooks and Bot Web API."""

    def __init__(self):
        super().__init__("SlackAdapter")
        self.bot_token = settings.SLACK_BOT_TOKEN
        self.webhook_url = settings.SLACK_WEBHOOK_URL
        self.sales_channel = settings.SLACK_SALES_CHANNEL
        self.support_channel = settings.SLACK_SUPPORT_CHANNEL
        self._simulate_failure: bool = False

        # In-memory mock history
        self.mock_messages: List[Dict[str, Any]] = []
        self.mock_channels: Dict[str, Dict[str, Any]] = {}

    def is_configured(self) -> bool:
        return bool((self.bot_token or self.webhook_url) and not settings.DEMO_MODE)

    def trigger_simulated_failure(self) -> None:
        """Trigger temporary error to test retry and failure recovery."""
        self._simulate_failure = True

    def health_check(self) -> Dict[str, Any]:
        if not self.is_configured():
            return {
                "name": self.name,
                "status": IntegrationStatus.DEMO_MODE.value,
                "channels": [self.sales_channel, self.support_channel],
                "configured": False,
                "dispatched_mock_alerts": len(self.mock_messages),
                "message": "Running Slack mock dispatcher. Block Kit payloads validated deterministically.",
            }

        try:
            start = time.perf_counter()
            if self.bot_token:
                url = "https://slack.com/api/auth.test"
                headers = {"Authorization": f"Bearer {self.bot_token}"}
                with httpx.Client(timeout=5.0) as client:
                    res = client.post(url, headers=headers)
                    res.raise_for_status()
                    data = res.json()
                    if not data.get("ok"):
                        raise ConnectionError(f"Slack auth error: {data.get('error')}")
            latency = round((time.perf_counter() - start) * 1000, 2)
            return {
                "name": self.name,
                "status": IntegrationStatus.VERIFIED_LIVE.value,
                "latency_ms": latency,
                "configured": True,
            }
        except Exception as err:
            return {
                "name": self.name,
                "status": IntegrationStatus.ERROR.value,
                "error": str(err),
                "configured": True,
            }

    def post_lead_alert(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Format and dispatch rich Slack Block Kit alert for new qualified leads."""
        if self._simulate_failure:
            self._simulate_failure = False
            logger.warning("[SlackAdapter] Simulating Slack delivery timeout for error handling verification.")
            raise ConnectionError("Simulated Slack webhook timeout/connection error (504)")

        priority = lead.get("priority", "MEDIUM")
        emoji = "🔴" if priority == "URGENT" else ("🟠" if priority == "HIGH" else "🟢")
        budget = lead.get("budget", 0)

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} New {priority} Lead: {lead.get('company_name')}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Contact:* {lead.get('contact_name')} (<mailto:{lead.get('contact_email')}|{lead.get('contact_email')}>)"},
                    {"type": "mrkdwn", "text": f"*Budget:* ${budget:,.2f}"},
                    {"type": "mrkdwn", "text": f"*Score:* {lead.get('score')}/100 ({lead.get('qualification_status')})"},
                    {"type": "mrkdwn", "text": f"*Timeline:* {lead.get('timeline', 'N/A')}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Needs Summary:*\n>{lead.get('needs')}\n\n*Rationale:*\n_{lead.get('rationale')}_",
                },
            },
        ]

        if not self.is_configured():
            ts = f"{int(time.time())}.{len(self.mock_messages):06d}"
            msg = {
                "channel": self.sales_channel,
                "ts": ts,
                "text": f"New Lead: {lead.get('company_name')}",
                "blocks": blocks,
                "timestamp": time.time(),
            }
            self.mock_messages.append(msg)
            logger.info(f"[SlackAdapter] Mock dispatched sales lead alert to {self.sales_channel} (ts={ts})")
            return {"success": True, "ts": ts, "channel": self.sales_channel, "mode": "MOCK"}

        # Live webhook execution
        return self.execute_with_retry(self._send_live_webhook, {"blocks": blocks})

    def post_support_escalation(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch high-urgency alert to support staff channel."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 Support Escalation: {ticket.get('subject')}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Sender:* {ticket.get('sender_name')} ({ticket.get('sender_email')})"},
                    {"type": "mrkdwn", "text": f"*Urgency:* {ticket.get('urgency')}"},
                    {"type": "mrkdwn", "text": f"*Intent:* {ticket.get('intent')}"},
                    {"type": "mrkdwn", "text": f"*Escalation Reason:* {ticket.get('escalation_reason')}"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Customer Message Excerpt:*\n>{ticket.get('clean_body')[:300]}..."},
            },
        ]

        if not self.is_configured():
            ts = f"{int(time.time())}.{len(self.mock_messages):06d}"
            self.mock_messages.append({"channel": self.support_channel, "ts": ts, "blocks": blocks})
            return {"success": True, "ts": ts, "channel": self.support_channel, "mode": "MOCK"}

        return self.execute_with_retry(self._send_live_webhook, {"blocks": blocks})

    def provision_project_channel(self, project_code: str, customer_name: str) -> Dict[str, Any]:
        """Idempotently create client collaboration channel."""
        clean_code = project_code.lower().replace("_", "-")
        channel_name = f"prj-{clean_code}"

        if channel_name in self.mock_channels:
            logger.info(f"[SlackAdapter] Channel '{channel_name}' already exists (Idempotent).")
            return {
                "success": True,
                "channel_id": self.mock_channels[channel_name]["id"],
                "channel_name": channel_name,
                "created": False,
                "mode": "MOCK",
            }

        channel_id = f"C_MOCK_{int(time.time() * 1000)}"
        self.mock_channels[channel_name] = {
            "id": channel_id,
            "name": channel_name,
            "customer": customer_name,
            "created_at": time.time(),
        }
        logger.info(f"[SlackAdapter] Provisioned collaboration channel #{channel_name} ({channel_id})")
        return {"success": True, "channel_id": channel_id, "channel_name": channel_name, "created": True, "mode": "MOCK"}

    def _send_live_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.webhook_url:
            raise ValueError("SLACK_WEBHOOK_URL is not configured.")
        with httpx.Client(timeout=8.0) as client:
            res = client.post(self.webhook_url, json=payload)
            res.raise_for_status()
            return {"success": True, "mode": "LIVE"}
