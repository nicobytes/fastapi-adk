"""Channel-agnostic outbound intent models for ADK reply tools."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

MAX_REPLY_BUTTONS = 3
MAX_BUTTON_TITLE_LENGTH = 20
MAX_LIST_BUTTON_LABEL = 20
MAX_LIST_SECTION_TITLE = 24
MAX_LIST_ROW_TITLE = 24
MAX_LIST_ROW_DESCRIPTION = 72
MAX_LIST_ROWS = 10  # WhatsApp: max rows across all sections
MAX_LIST_SECTIONS = 10
MAX_INTERACTIVE_BODY = 1024


class ReplyButton(BaseModel):
    id: str = Field(min_length=1, max_length=256)
    title: str = Field(min_length=1, max_length=MAX_BUTTON_TITLE_LENGTH)


class ListRow(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=MAX_LIST_ROW_TITLE)
    description: str | None = Field(default=None, max_length=MAX_LIST_ROW_DESCRIPTION)


class ListSection(BaseModel):
    title: str = Field(min_length=1, max_length=MAX_LIST_SECTION_TITLE)
    rows: list[ListRow] = Field(min_length=1, max_length=MAX_LIST_ROWS)


class TextIntent(BaseModel):
    type: Literal["text"] = "text"
    body: str = Field(min_length=1)


class ButtonsIntent(BaseModel):
    type: Literal["buttons"] = "buttons"
    body: str = Field(min_length=1, max_length=MAX_INTERACTIVE_BODY)
    header: str | None = Field(default=None, max_length=60)
    buttons: list[ReplyButton] = Field(min_length=1, max_length=MAX_REPLY_BUTTONS)


class ListIntent(BaseModel):
    type: Literal["list"] = "list"
    body: str = Field(min_length=1, max_length=MAX_INTERACTIVE_BODY)
    button_label: str = Field(
        min_length=1,
        max_length=MAX_LIST_BUTTON_LABEL,
        serialization_alias="buttonLabel",
    )
    sections: list[ListSection] = Field(min_length=1, max_length=MAX_LIST_SECTIONS)

    model_config = {"populate_by_name": True}


class LocationIntent(BaseModel):
    type: Literal["location"] = "location"
    latitude: float
    longitude: float
    name: str | None = None
    address: str | None = None

    @field_validator("latitude")
    @classmethod
    def _lat(cls, v: float) -> float:
        if not -90 <= v <= 90:
            raise ValueError("latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    @classmethod
    def _lng(cls, v: float) -> float:
        if not -180 <= v <= 180:
            raise ValueError("longitude must be between -180 and 180")
        return v


class TemplateIntent(BaseModel):
    type: Literal["template"] = "template"
    name: str = Field(min_length=1)
    language: str = Field(min_length=2)
    components: list[dict[str, Any]] | None = None


OutboundIntent = (
    TextIntent | ButtonsIntent | ListIntent | LocationIntent | TemplateIntent
)


class IntentToolResult(BaseModel):
    """Stable envelope Nest parses from functionResponse."""

    kind: Literal["outbound_intent"] = "outbound_intent"
    intent: OutboundIntent

    def to_response_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)


class IntentBatchResult(BaseModel):
    """Additive envelope: several intents in one functionResponse (send order)."""

    kind: Literal["outbound_intent_batch"] = "outbound_intent_batch"
    intents: list[OutboundIntent] = Field(min_length=1, max_length=3)

    def to_response_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)
