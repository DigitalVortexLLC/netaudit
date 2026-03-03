"""WebSocket consumers for live audit updates."""

import json

from channels.generic.websocket import AsyncWebsocketConsumer


class DashboardConsumer(AsyncWebsocketConsumer):
    """
    Broadcasts live updates to the dashboard.

    Clients receive messages when audits are created, change status,
    or complete — letting the dashboard update stats and the recent
    audits table in real time.
    """

    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
            return

        self.group_name = "dashboard"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name, self.channel_name
            )

    async def audit_update(self, event):
        """Handle audit status change broadcast."""
        await self.send(text_data=json.dumps(event["data"]))


class AuditDetailConsumer(AsyncWebsocketConsumer):
    """
    Broadcasts live progress for a single audit run.

    Clients receive status transitions and individual rule results
    as they arrive, so the detail page updates without polling.
    """

    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
            return

        self.audit_id = self.scope["url_route"]["kwargs"]["audit_id"]
        self.group_name = f"audit_{self.audit_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name, self.channel_name
            )

    async def audit_status(self, event):
        """Handle audit status change."""
        await self.send(text_data=json.dumps(event["data"]))

    async def audit_result(self, event):
        """Handle individual rule result."""
        await self.send(text_data=json.dumps(event["data"]))
