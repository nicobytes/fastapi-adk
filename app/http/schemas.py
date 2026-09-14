from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class InboundRequest(BaseModel):
    wa_id: str | None = Field(default=None, alias="waId")
    session_id: str | None = Field(default=None, alias="sessionId")
    text: str = Field(min_length=1)
    agent_id: str | None = Field(default=None, alias="agentId")

    model_config = {"populate_by_name": True}


class InboundResponse(BaseModel):
    conversation_id: str = Field(alias="conversationId")
    status: str
    accepted: bool = True

    model_config = {"populate_by_name": True, "ser_json_by_alias": True}


class InteractiveRequest(BaseModel):
    conversation_id: str | None = Field(default=None, alias="conversationId")
    session_id: str | None = Field(default=None, alias="sessionId")
    button_id: str = Field(min_length=1, alias="buttonId")
    agent_id: str | None = Field(default=None, alias="agentId")

    model_config = {"populate_by_name": True}


class InteractiveResponse(BaseModel):
    conversation_id: str = Field(alias="conversationId")
    accepted: bool = True

    model_config = {"populate_by_name": True, "ser_json_by_alias": True}


class OperatorReplyRequest(BaseModel):
    conversation_id: str | None = Field(default=None, alias="conversationId")
    session_id: str | None = Field(default=None, alias="sessionId")
    text: str = Field(min_length=1)

    model_config = {"populate_by_name": True}


class OperatorReplyResponse(BaseModel):
    conversation_id: str = Field(alias="conversationId")
    accepted: bool = True

    model_config = {"populate_by_name": True, "ser_json_by_alias": True}


class StatusResponse(BaseModel):
    conversation_id: str = Field(alias="conversationId")
    status: str

    model_config = {"populate_by_name": True, "ser_json_by_alias": True}


class HealthResponse(BaseModel):
    ok: Literal[True] = True
