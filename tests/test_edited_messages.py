from unittest.mock import AsyncMock

import pytest

import bot


CASES = [
    ("Hello", "private"),
    ("@test_bot Hello", "group"),
    ("/ask Hello", "group"),
    ("/start", "private"),
    ("/help", "private"),
    ("/reset", "private"),
]


@pytest.mark.parametrize("text,chat_type", CASES)
async def test_new_messages_match_handlers(application, make_update, text, chat_type):
    update = make_update(text, chat_type=chat_type)
    assert any(handler.check_update(update) for handler in application.handlers[0])


@pytest.mark.parametrize("text,chat_type", CASES)
async def test_edited_messages_do_not_match_handlers(application, make_update, text, chat_type):
    update = make_update(text, edited=True, chat_type=chat_type)
    assert not any(handler.check_update(update) for handler in application.handlers[0])


@pytest.mark.parametrize("text,chat_type", CASES)
async def test_edit_has_no_side_effects(
    application, fake_bot, make_update, monkeypatch, text, chat_type
):
    llm = AsyncMock(return_value="Answer")
    errors = AsyncMock()
    monkeypatch.setattr(bot, "ask_llm", llm)
    application.add_error_handler(errors)
    await application.process_update(make_update(text, chat_type=chat_type))
    assert fake_bot.send_message.await_count == 1
    fake_bot.send_message.reset_mock()
    llm.reset_mock()
    turn = {"role": "user", "content": "Keep this turn"}
    bot.history[123].append(turn)

    await application.process_update(
        make_update(text, edited=True, chat_type=chat_type, update_id=2)
    )

    errors.assert_not_awaited()
    fake_bot.send_message.assert_not_awaited()
    llm.assert_not_awaited()
    assert list(bot.history[123]) == [turn]


@pytest.mark.parametrize("text", [None, ""])
async def test_empty_messages_are_ignored(application, fake_bot, make_update, text):
    await application.process_update(make_update(text))
    fake_bot.send_message.assert_not_awaited()
