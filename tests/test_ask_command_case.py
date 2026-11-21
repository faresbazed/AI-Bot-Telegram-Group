from unittest.mock import AsyncMock

import pytest

import bot


@pytest.mark.parametrize("command", ["/ask", "/ASK", "/Ask@{username}"])
async def test_ask_command_strips_case_insensitively(
    application, fake_bot, make_update, monkeypatch, command
):
    llm = AsyncMock(return_value="Answer")
    errors = AsyncMock()
    monkeypatch.setattr(bot, "ask_llm", llm)
    application.add_error_handler(errors)
    command = command.format(username=fake_bot.username)

    await application.process_update(make_update(f"{command} hi", chat_type="group"))

    errors.assert_not_awaited()
    llm.assert_awaited_once_with(123, "hi")
