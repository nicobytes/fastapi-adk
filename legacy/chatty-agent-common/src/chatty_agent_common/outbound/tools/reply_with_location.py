"""Pure ADK tool: queue a location pin outbound intent."""

from __future__ import annotations

from typing import Any

from chatty_agent_common.outbound.models import IntentToolResult, LocationIntent


def reply_with_location(
    latitude: float,
    longitude: float,
    name: str | None = None,
    address: str | None = None,
) -> dict[str, Any]:
    """Queue a location pin (lat/lng) with optional name and address."""
    intent = LocationIntent(
        latitude=latitude,
        longitude=longitude,
        name=name,
        address=address,
    )
    return IntentToolResult(intent=intent).to_response_dict()
