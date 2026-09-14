"""Tenant-agnostic booking via Chatty Nest API."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from chatty_agent_common.providers.chatty_api import api_request
from chatty_agent_common.providers.supabase import get_organization_slug

logger = logging.getLogger(__name__)


def run_book_appointment(
    *,
    organization_slug: str,
    schedule_slug: str,
    service_name: str,
    slot_id: str,
    duration_minutes: int | None = None,
    conversation_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    timezone: str = "UTC",
) -> dict[str, Any]:
    """Book an appointment via Chatty NestJS API.

    Call only after the customer picks a ``slot_id`` from
    ``run_check_availability``.

    Args:
        organization_slug: ``organizations.slug`` for the tenant.
        schedule_slug: Platform schedule slug.
        service_name: Human-readable service label (stored on the booking).
        slot_id: Exact id from ``run_check_availability``.
        duration_minutes: Optional appointment length override (from RAG).
        conversation_id: ADK session id (= ``conversations.id``) so Nest can
            attach ``bookings.customer_id`` from the conversation.
        metadata: Optional booking metadata forwarded to Nest.
        timezone: IANA timezone for the confirmation label.
    """
    cleaned_slug = (organization_slug or "").strip()
    if not cleaned_slug:
        return {"status": "error", "message": "organization_slug cannot be empty"}

    cleaned_schedule = (schedule_slug or "").strip()
    if not cleaned_schedule:
        return {"status": "error", "message": "schedule_slug cannot be empty"}

    cleaned_service = (service_name or "").strip()
    if not cleaned_service:
        return {"status": "error", "message": "service_name cannot be empty"}

    sid = (slot_id or "").strip()
    if not sid:
        return {
            "status": "error",
            "message": "Missing slot_id. Call check availability first.",
        }

    try:
        tz = ZoneInfo(timezone)
    except Exception:
        return {"status": "error", "message": f"Invalid timezone: {timezone}"}

    try:
        body: dict[str, Any] = {
            "organizationId": get_organization_slug(cleaned_slug),
            "scheduleSlug": cleaned_schedule,
            "serviceName": cleaned_service,
            "slotId": sid,
            "metadata": metadata or {},
        }
        if duration_minutes is not None:
            body["durationMinutes"] = int(duration_minutes)
        cleaned_conversation = (conversation_id or "").strip()
        if cleaned_conversation:
            body["conversationId"] = cleaned_conversation

        booking = api_request(
            "POST",
            "/scheduling/bookings",
            body=body,
        )
    except (RuntimeError, ValueError) as exc:
        logger.exception("run_book_appointment failed")
        message = str(exc)
        if "409" in message or "Conflict" in message:
            return {
                "status": "error",
                "message": (
                    "That slot is no longer available. Check availability "
                    "again and offer other times."
                ),
            }
        return {"status": "error", "message": message}

    if not isinstance(booking, dict) or not booking.get("id"):
        return {
            "status": "error",
            "message": "Invalid response when creating the booking.",
        }

    start_raw = str(booking.get("startAt") or booking.get("start_at") or "")
    label = start_raw
    if start_raw:
        try:
            start = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
            local = start.astimezone(tz)
            label = f"{local.date().isoformat()} {local.strftime('%H:%M')}"
        except ValueError:
            pass

    booking_id = str(booking["id"])
    logger.info(
        "Booking created booking_id=%s schedule=%s slot_id=%s",
        booking_id,
        cleaned_schedule,
        sid,
    )

    return {
        "status": "booked",
        "booking": {
            "booking_id": booking_id,
            "slot_id": sid,
            "schedule_slug": cleaned_schedule,
            "service_name": cleaned_service,
            "duration_minutes": duration_minutes,
            "label": label,
        },
        "message": (
            "Appointment booked. Confirm details with the customer. "
            "Do not hand off to a human."
        ),
    }
