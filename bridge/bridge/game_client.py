"""HTTP client for the Songs of Syx LLM Overlord mod API."""
from __future__ import annotations

import logging

import httpx

from .models import GameState, Command, CommandResult

logger = logging.getLogger(__name__)


class GameClient:
    """Communicates with the Java mod's embedded HTTP server."""

    def __init__(self, base_url: str = "http://localhost:47823"):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=10.0)

    def health_check(self) -> bool:
        """Check if the mod API is reachable."""
        try:
            resp = self._client.get(f"{self.base_url}/api/health")
            return resp.status_code == 200
        except httpx.RequestError:
            return False

    def get_state(self) -> GameState:
        """Fetch current game state from the mod."""
        resp = self._client.get(f"{self.base_url}/api/state")
        resp.raise_for_status()
        return GameState.model_validate(resp.json())

    def send_command(self, command: Command) -> CommandResult:
        """Send a command to the mod for execution."""
        resp = self._client.post(
            f"{self.base_url}/api/command",
            json=command.model_dump(exclude_none=True),
        )
        data = resp.json()
        return CommandResult(success=data.get("success", False), message=data.get("message", ""))

    def get_info(self) -> dict:
        """Get mod info."""
        resp = self._client.get(f"{self.base_url}/api/info")
        resp.raise_for_status()
        return resp.json()

    def close(self):
        self._client.close()
