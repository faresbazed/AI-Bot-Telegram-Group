import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from telegram import Chat, Message, MessageEntity, Update, User
from telegram.ext import ApplicationBuilder, ExtBot

with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "", "OPENAI_API_KEY": ""}):
    import bot


@pytest.fixture
def fake_bot():
    client = MagicMock(spec=ExtBot)
    client.id = 999
    client.username = "test_bot"
    client.initialize = AsyncMock()
    client.shutdown = AsyncMock()
    client.send_message = AsyncMock()
    client.send_chat_action = AsyncMock()
    return client


@pytest.fixture(autouse=True)
def isolated_state(monkeypatch):
    monkeypatch.setattr(bot, "ALLOWED_CHAT_IDS", set())
    monkeypatch.setattr(bot, "RESPOND_MODE", "mention_only")
    bot.history.clear()
    yield
    bot.history.clear()


@pytest_asyncio.fixture
async def application(fake_bot):
    app = ApplicationBuilder().bot(fake_bot).updater(None).build()
    bot.register_handlers(app)
    async with app:
        yield app


@pytest.fixture
def make_update(fake_bot):
    def factory(text="Hello", *, edited=False, chat_type="private", update_id=1, **message_fields):
        entities = []
        if text and text.startswith("/"):
            entities.append(MessageEntity(MessageEntity.BOT_COMMAND, 0, len(text.split()[0])))
        message_fields.setdefault("message_id", 1)
        message_fields.setdefault("from_user", User(456, "Tester", False))
        message = Message(
            date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            chat=Chat(123, chat_type),
            text=text,
            entities=entities,
            **message_fields,
        )
        message.set_bot(fake_bot)
        update = Update(update_id, **{"edited_message" if edited else "message": message})
        update.set_bot(fake_bot)
        return update

    return factory
