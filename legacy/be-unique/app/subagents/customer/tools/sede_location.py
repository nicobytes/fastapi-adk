"""Canonical Be Unique sede pins and ``send_sede_location`` outbound tool.

The model passes a sede name (or ``ambas``), never latitude/longitude.
See ``specs/008-sede-location-card/contracts/send-sede-location.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from google.adk.tools.tool_context import ToolContext

from chatty_agent_common.outbound.models import (
    IntentBatchResult,
    IntentToolResult,
    LocationIntent,
    OutboundIntent,
    TextIntent,
)

SedeKey = Literal["sucre", "cochabamba"]


@dataclass(frozen=True)
class SedePin:
    key: SedeKey
    display_name: str
    address: str
    latitude: float
    longitude: float
    maps_ref: str


SEDE_SUCRE = SedePin(
    key="sucre",
    display_name="Be Unique — Sucre",
    address="Calle Destacamento 317 #994, Barrio Petrolero, Sucre, Bolivia",
    latitude=-19.0401406,
    longitude=-65.2444091,
    maps_ref="https://maps.app.goo.gl/s3b4WgTawMfGxK1K7",
)

SEDE_COCHABAMBA = SedePin(
    key="cochabamba",
    display_name="Be Unique — Cochabamba",
    address=(
        "Calle A. M. Torrico esq. Av. América, Edificio Altos Casah, "
        "1er piso of. F, Queru Queru, Cochabamba, Bolivia"
    ),
    latitude=-17.373292,
    longitude=-66.155718,
    maps_ref="https://maps.app.goo.gl/jKgwohwsWPyJ9FvL9",
)

SEDE_PINS: dict[SedeKey, SedePin] = {
    "sucre": SEDE_SUCRE,
    "cochabamba": SEDE_COCHABAMBA,
}

_SUCRE_ALIASES = frozenset(
    {
        "sucre",
        "sede_sucre",
        "sede sucre",
        "be unique — sucre",
        "be unique - sucre",
        "be unique sucre",
    }
)
_COCHABAMBA_ALIASES = frozenset(
    {
        "cochabamba",
        "sede_cochabamba",
        "sede cochabamba",
        "be unique — cochabamba",
        "be unique - cochabamba",
        "be unique cochabamba",
    }
)
_AMBAS_ALIASES = frozenset({"ambas", "ambas sedes", "ambas_sedes"})

_UNKNOWN_SEDE = (
    "Indique Sucre o Cochabamba. No se envía el pin hasta identificar la sede."
)
_AMBAS_WITH_BODY = (
    "La confirmación de una cita es de una sola sede. "
    "Pase Sucre o Cochabamba, no ambas."
)


def _normalize_sede_token(sede: str) -> str:
    return " ".join(sede.strip().casefold().replace("_", " ").split())


def resolve_sede_pin(sede: str) -> list[SedePin]:
    """Resolve catalog pins. Empty list if the token is unknown.

    Aliases: ``Sucre``, ``sede_sucre``, ``Cochabamba``, ``sede_cochabamba``,
    ``ambas`` / ``ambas sedes``.
    """
    token = _normalize_sede_token(sede)
    if not token:
        return []
    if token in _AMBAS_ALIASES:
        return [SEDE_SUCRE, SEDE_COCHABAMBA]
    compact = token.replace(" ", "_")
    if token in _SUCRE_ALIASES or compact in {"sucre", "sede_sucre"}:
        return [SEDE_SUCRE]
    if token in _COCHABAMBA_ALIASES or compact in {
        "cochabamba",
        "sede_cochabamba",
    }:
        return [SEDE_COCHABAMBA]
    return []


def _sede_from_context(tool_context: ToolContext | None) -> str:
    if tool_context is None:
        return ""
    state = getattr(tool_context, "state", None)
    if state is None:
        return ""
    for key in ("active_sede", "active_schedule_slug"):
        value = state.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _location_intent(pin: SedePin) -> LocationIntent:
    return LocationIntent(
        latitude=pin.latitude,
        longitude=pin.longitude,
        name=pin.display_name,
        address=pin.address,
    )


def _error(message: str) -> dict[str, Any]:
    return {"status": "error", "message": message}


def send_sede_location(
    sede: str,
    tool_context: ToolContext,
    body: str | None = None,
) -> dict[str, Any]:
    """Envía el pin nativo de WhatsApp de la sede Be Unique (Sucre o Cochabamba).

    Use esta tool — nunca ``reply_with_location`` ni un enlace de Maps — cuando
    el cliente pida dirección, mapa, ubicación o cómo llegar, o para confirmar
    / reagendar una cita (entonces pase ``body`` con el texto de confirmación).

    El pin usa coordenadas canónicas; no invente latitud ni longitud.

    Args:
        sede: Nombre, slug o alias (``Sucre``, ``sede_sucre``, ``Cochabamba``,
            ``ambas``). Vacío: usa ``active_sede`` del estado (pedido de mapa).
            En confirmación de cita MUST ser la sede reservada (nunca ``ambas``).
        body: Si está presente y no vacío, confirmación de cita o reagendado:
            se envía como texto **antes** del pin. Omitir en pedido de mapa
            (el pin basta).
    """
    cleaned_body = body.strip() if isinstance(body, str) and body.strip() else None
    pins = resolve_sede_pin(sede)
    if not pins:
        pins = resolve_sede_pin(_sede_from_context(tool_context))
    if not pins:
        return _error(_UNKNOWN_SEDE)
    if cleaned_body and len(pins) > 1:
        return _error(_AMBAS_WITH_BODY)

    locations: list[OutboundIntent] = [_location_intent(pin) for pin in pins]
    if cleaned_body:
        return IntentBatchResult(
            intents=[TextIntent(body=cleaned_body), *locations]
        ).to_response_dict()
    if len(locations) == 1:
        return IntentToolResult(intent=locations[0]).to_response_dict()
    return IntentBatchResult(intents=locations).to_response_dict()
