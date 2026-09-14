from __future__ import annotations

import pytest

from app.channel.service import ChannelService
from app.conversations.inbox_view import to_inbox
from app.conversations.store import ConversationStore
from app.conversations.types import ChoiceOption


@pytest.mark.asyncio
async def test_channel_crm_mapping_buttons_and_location(tmp_path) -> None:
    store = ConversationStore(f"sqlite+aiosqlite:///{tmp_path / 'poc.sqlite'}")
    await store.connect()
    try:
        channel = ChannelService(store)
        conv = await store.find_or_create_open("crm-1")
        channel.bind(conv.id, "fake", "crm-1")
        await channel.send_buttons(
            conv.id,
            "pick",
            [ChoiceOption(id="a", title="A"), ChoiceOption(id="b", title="B")],
            function_call_id="fc-xyz",
        )
        await channel.send_location(conv.id, latitude=1.0, longitude=2.0, name="pin")
        messages = await store.list_messages(conv.id)
        inbox = to_inbox(messages)
        buttons = next(m for m in inbox if m["kind"] == "buttons")
        location = next(m for m in inbox if m["kind"] == "location")
        assert buttons["payload"]["options"][0]["id"] == "a"
        assert location["payload"]["latitude"] == 1.0
        assert "functionCallId" in buttons["payload"]
    finally:
        await store.close()
