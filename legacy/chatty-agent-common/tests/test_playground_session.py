"""Playground → local Supabase conversation bridge (ADK_DEV_MODE)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from chatty_agent_common.playground_session import (
    PLAYGROUND_READY_STATE_KEY,
    PLAYGROUND_SOURCE,
    ensure_playground_conversation,
    is_local_supabase_url,
    make_ensure_playground_conversation_callback,
    playground_conversation_id,
)

SESSION_ID = "0ad38675-6623-46c8-aaea-354d0869d808"
ORG_ID = "11111111-1111-4111-8111-111111111111"
INBOX_ID = "22222222-2222-4222-8222-222222222222"
CUSTOMER_ID = "33333333-3333-4333-8333-333333333333"


def test_is_local_supabase_url() -> None:
    assert is_local_supabase_url("http://127.0.0.1:54321") is True
    assert is_local_supabase_url("http://localhost:54321") is True
    assert is_local_supabase_url("http://[::1]:54321") is True
    assert is_local_supabase_url("https://xyz.supabase.co") is False
    assert is_local_supabase_url("") is False
    assert is_local_supabase_url("not-a-url") is False


def test_ensure_skips_when_dev_mode_off(monkeypatch) -> None:
    monkeypatch.delenv("ADK_DEV_MODE", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "http://127.0.0.1:54321")
    result = ensure_playground_conversation(SESSION_ID, "be-unique")
    assert result == {"status": "skipped", "reason": "adk_dev_mode_off"}


def test_ensure_skips_non_local_supabase(monkeypatch) -> None:
    monkeypatch.setenv("ADK_DEV_MODE", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
    result = ensure_playground_conversation(SESSION_ID, "be-unique")
    assert result == {"status": "skipped", "reason": "non_local_supabase"}


def test_ensure_rejects_invalid_session_id(monkeypatch) -> None:
    monkeypatch.setenv("ADK_DEV_MODE", "true")
    monkeypatch.setenv("SUPABASE_URL", "http://127.0.0.1:54321")
    result = ensure_playground_conversation("not-a-uuid", "be-unique")
    assert result["status"] == "error"
    assert "valid UUID" in result["message"]


def test_ensure_returns_exists_when_row_present(monkeypatch) -> None:
    monkeypatch.setenv("ADK_DEV_MODE", "true")
    monkeypatch.setenv("SUPABASE_URL", "http://127.0.0.1:54321")

    with patch(
        "chatty_agent_common.playground_session._conversation_exists",
        return_value=True,
    ):
        result = ensure_playground_conversation(SESSION_ID, "be-unique")

    assert result == {
        "status": "exists",
        "conversation_id": SESSION_ID,
    }


def _mock_client_for_create(*, with_inbox_query: bool) -> MagicMock:
    client = MagicMock()
    conversations = MagicMock()
    customers = MagicMock()
    inboxes = MagicMock()

    def table_factory(name: str) -> MagicMock:
        mapping = {
            "conversations": conversations,
            "customers": customers,
            "inboxes": inboxes,
        }
        return mapping[name]

    client.table.side_effect = table_factory
    client._conversations = conversations
    client._customers = customers
    client._inboxes = inboxes

    conversations.select.return_value.eq.return_value.limit.return_value.execute.return_value = SimpleNamespace(
        data=[]
    )
    if with_inbox_query:
        inboxes.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = SimpleNamespace(
            data=[{"id": INBOX_ID}]
        )
    customers.insert.return_value.execute.return_value = SimpleNamespace(
        data=[{"id": CUSTOMER_ID}]
    )
    conversations.insert.return_value.execute.return_value = SimpleNamespace(
        data=[{"id": SESSION_ID}]
    )
    return client


def test_ensure_creates_customer_and_conversation(monkeypatch) -> None:
    monkeypatch.setenv("ADK_DEV_MODE", "true")
    monkeypatch.setenv("SUPABASE_URL", "http://127.0.0.1:54321")
    monkeypatch.delenv("ADK_DEV_INBOX_ID", raising=False)

    client = _mock_client_for_create(with_inbox_query=True)

    with (
        patch(
            "chatty_agent_common.playground_session.get_supabase_client",
            return_value=client,
        ),
        patch(
            "chatty_agent_common.playground_session.get_organization_slug",
            return_value=ORG_ID,
        ),
    ):
        result = ensure_playground_conversation(SESSION_ID, "be-unique")

    assert result == {
        "status": "created",
        "conversation_id": SESSION_ID,
        "customer_id": CUSTOMER_ID,
        "inbox_id": INBOX_ID,
        "organization_id": ORG_ID,
    }

    insert_payload = client._customers.insert.call_args.args[0]
    assert insert_payload["organization_id"] == ORG_ID
    assert insert_payload["name"] == "Playground User"
    assert insert_payload["phone"] is None
    assert insert_payload["metadata"]["source"] == PLAYGROUND_SOURCE

    conv_payload = client._conversations.insert.call_args.args[0]
    assert conv_payload["id"] == SESSION_ID
    assert conv_payload["inbox_id"] == INBOX_ID
    assert conv_payload["customer_id"] == CUSTOMER_ID
    assert conv_payload["status"] == "AI_AUTO"
    assert conv_payload["stage"] == "first_contact"
    assert conv_payload["metadata"]["source"] == PLAYGROUND_SOURCE


def test_ensure_idempotent_second_call(monkeypatch) -> None:
    monkeypatch.setenv("ADK_DEV_MODE", "true")
    monkeypatch.setenv("SUPABASE_URL", "http://127.0.0.1:54321")
    monkeypatch.delenv("ADK_DEV_INBOX_ID", raising=False)

    client = _mock_client_for_create(with_inbox_query=True)

    with (
        patch(
            "chatty_agent_common.playground_session.get_supabase_client",
            return_value=client,
        ),
        patch(
            "chatty_agent_common.playground_session.get_organization_slug",
            return_value=ORG_ID,
        ),
        patch(
            "chatty_agent_common.playground_session._conversation_exists",
            side_effect=[False, True],
        ),
    ):
        first = ensure_playground_conversation(SESSION_ID, "be-unique")
        second = ensure_playground_conversation(SESSION_ID, "be-unique")

    assert first["status"] == "created"
    assert second == {"status": "exists", "conversation_id": SESSION_ID}
    assert client._customers.insert.call_count == 1
    assert client._conversations.insert.call_count == 1


def test_callback_sets_ready_state_on_success(monkeypatch) -> None:
    monkeypatch.setenv("ADK_DEV_MODE", "true")
    state: dict = {}
    callback_context = SimpleNamespace(
        state=state,
        session=SimpleNamespace(id=SESSION_ID),
    )
    callback = make_ensure_playground_conversation_callback("be-unique")

    with patch(
        "chatty_agent_common.playground_session.ensure_playground_conversation",
        return_value={"status": "created", "conversation_id": SESSION_ID},
    ) as ensure:
        assert callback(callback_context) is None  # type: ignore[arg-type]
        ensure.assert_called_once_with(SESSION_ID, "be-unique")

    assert state[PLAYGROUND_READY_STATE_KEY] is True

    with patch(
        "chatty_agent_common.playground_session.ensure_playground_conversation",
    ) as ensure_again:
        assert callback(callback_context) is None  # type: ignore[arg-type]
        ensure_again.assert_not_called()


def test_callback_noop_when_dev_mode_off(monkeypatch) -> None:
    monkeypatch.delenv("ADK_DEV_MODE", raising=False)
    state: dict = {}
    callback_context = SimpleNamespace(
        state=state,
        session=SimpleNamespace(id=SESSION_ID),
    )
    callback = make_ensure_playground_conversation_callback("be-unique")

    with patch(
        "chatty_agent_common.playground_session.ensure_playground_conversation",
    ) as ensure:
        assert callback(callback_context) is None  # type: ignore[arg-type]
        ensure.assert_not_called()

    assert PLAYGROUND_READY_STATE_KEY not in state


def test_playground_conversation_id_prod_always_returns_session(
    monkeypatch,
) -> None:
    monkeypatch.delenv("ADK_DEV_MODE", raising=False)
    ctx = SimpleNamespace(
        state={},
        session=SimpleNamespace(id=SESSION_ID),
    )
    assert playground_conversation_id(ctx) == SESSION_ID


def test_playground_conversation_id_dev_ready(monkeypatch) -> None:
    monkeypatch.setenv("ADK_DEV_MODE", "true")
    ctx = SimpleNamespace(
        state={PLAYGROUND_READY_STATE_KEY: True},
        session=SimpleNamespace(id=SESSION_ID),
    )
    assert playground_conversation_id(ctx) == SESSION_ID


def test_playground_conversation_id_dev_not_ready(monkeypatch) -> None:
    monkeypatch.setenv("ADK_DEV_MODE", "true")
    ctx = SimpleNamespace(
        state={},
        session=SimpleNamespace(id=SESSION_ID),
    )
    assert playground_conversation_id(ctx) is None


def test_ensure_uses_adk_dev_inbox_id_override(monkeypatch) -> None:
    monkeypatch.setenv("ADK_DEV_MODE", "true")
    monkeypatch.setenv("SUPABASE_URL", "http://127.0.0.1:54321")
    monkeypatch.setenv("ADK_DEV_INBOX_ID", INBOX_ID)

    client = _mock_client_for_create(with_inbox_query=False)

    with (
        patch(
            "chatty_agent_common.playground_session.get_supabase_client",
            return_value=client,
        ),
        patch(
            "chatty_agent_common.playground_session.get_organization_slug",
            return_value=ORG_ID,
        ),
    ):
        result = ensure_playground_conversation(SESSION_ID, "be-unique")

    assert result["status"] == "created"
    assert result["inbox_id"] == INBOX_ID
    assert all(c.args[0] != "inboxes" for c in client.table.call_args_list)
