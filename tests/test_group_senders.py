from unittest.mock import AsyncMock

import pytest
from telegram import Chat, User

import bot


@pytest.mark.parametrize(
    "sender,sender_chat",
    [
        pytest.param(
            User(1087968824, "Group", True, username="GroupAnonymousBot"),
            Chat(123, "supergroup"),
            id="anonymous-admin",
        ),
        pytest.param(
            User(136817688, "Channel", True, username="Channel_Bot"),
            Chat(-1001234567890, "channel"),
            id="send-as-channel",
        ),
    ],
)
@pytest.mark.parametrize(
    "text,is_reply",
    [
        pytest.param("@test_bot Hello", False, id="mention"),
        pytest.param("Hello", True, id="reply"),
        pytest.param("/ask Hello", False, id="ask"),
    ],
)
async def test_group_chat_sender_can_address_bot(
    application, fake_bot, make_update, monkeypatch, sender, sender_chat, text, is_reply
):
    llm = AsyncMock(return_value="Answer")
    monkeypatch.setattr(bot, "ask_llm", llm)
    reply_to = None
    if is_reply:
        reply_to = make_update(
            chat_type="supergroup", from_user=User(fake_bot.id, "Bot", True), message_id=2
        ).message
    update = make_update(
        text,
        chat_type="supergroup",
        from_user=sender,
        sender_chat=sender_chat,
        reply_to_message=reply_to,
    )

    await application.process_update(update)

    llm.assert_awaited_once_with(update.effective_chat.id, "Hello")
    fake_bot.send_message.assert_awaited_once()


@pytest.mark.parametrize("sender_kind", ["other-bot", "self", "linked-channel-forward"])
async def test_nonhuman_group_messages_still_ignored(
    application, fake_bot, make_update, monkeypatch, sender_kind
):
    llm = AsyncMock(return_value="Answer")
    monkeypatch.setattr(bot, "ask_llm", llm)
    monkeypatch.setattr(bot, "RESPOND_MODE", "all")
    forwarded = sender_kind == "linked-channel-forward"
    sender_id = {"other-bot": 789, "self": fake_bot.id, "linked-channel-forward": 136817688}
    update = make_update(
        "@test_bot Hello",
        chat_type="supergroup",
        from_user=User(sender_id[sender_kind], "Bot", True),
        sender_chat=Chat(-1001234567890, "channel") if forwarded else None,
        is_automatic_forward=forwarded,
    )

    await application.process_update(update)

    llm.assert_not_awaited()
    fake_bot.send_message.assert_not_awaited()
