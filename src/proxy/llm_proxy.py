import logging

import httpx

from src.config import ANTHROPIC_API_KEY, ANTHROPIC_API_URL, ANTHROPIC_DEFAULT_MODEL

logger = logging.getLogger(__name__)


class LLMProxy:
    """Async proxy that forwards requests to the Anthropic Messages API."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=60.0)

    async def send(self, body: dict) -> dict:
        """Forward a messages-style request to Anthropic and return the JSON response."""
        if not ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env file."
            )

        # Ensure a model is specified
        if "model" not in body:
            body["model"] = ANTHROPIC_DEFAULT_MODEL

        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        logger.info("Forwarding request to Anthropic (model=%s)", body.get("model"))
        response = await self._client.post(ANTHROPIC_API_URL, json=body, headers=headers)
        response.raise_for_status()
        data: dict = response.json()
        logger.info("Received Anthropic response (stop_reason=%s)", data.get("stop_reason"))
        return data

    async def close(self) -> None:
        await self._client.aclose()
