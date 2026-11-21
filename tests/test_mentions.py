from unittest.mock import AsyncMock

import pytest

import bot


@pytest.mark.parametrize("suffix", ["_fan", "Helper", "123"])
async def test_longer_usernames_do_not_trigger_reply(
    application, fake_bot, make_update, monkeypatch, suffix
):
    llm = AsyncMock(return_value="Answer")
    monkeypatch.setattr(bot, "ask_llm", llm)

    await application.process_update(
        make_update(f"@{fake_bot.username}{suffix} hi", chat_type="group")
    )

    llm.assert_not_awaited()
    fake_bot.send_message.assert_not_awaited()


@pytest.mark.parametrize(
    "template,question",
    [
        ("@{username} hi", "hi"),
        ("@{upper} hi", "hi"),
        ("hey @{username} what's up", "hey  what's up"),
        ("@{username}, hi", ", hi"),
        ("@{username}أهلاً", "أهلاً"),
    ],
)
async def test_exact_mentions_reply_with_clean_question(
    application, fake_bot, make_update, monkeypatch, template, question
):
    llm = AsyncMock(return_value="Answer")
    monkeypatch.setattr(bot, "ask_llm", llm)
    text = template.format(username=fake_bot.username, upper=fake_bot.username.upper())

    await application.process_update(make_update(text, chat_type="group"))

    llm.assert_awaited_once_with(123, question)
    fake_bot.send_message.assert_awaited_once()


@pytest.mark.parametrize("text", ["", "@test_bot", "@TEST_BOT"])
async def test_empty_question_does_not_call_llm(
    application, fake_bot, make_update, monkeypatch, text
):
    llm = AsyncMock(return_value="Answer")
    monkeypatch.setattr(bot, "ask_llm", llm)

    await application.process_update(make_update(text, chat_type="group"))

    llm.assert_not_awaited()
    fake_bot.send_message.assert_not_awaited()


@pytest.mark.parametrize("suffix", ["_fan", "Helper", "123"])
def test_clean_question_preserves_other_usernames(fake_bot, suffix):
    text = f"@{fake_bot.username}{suffix} hi"
    assert bot.clean_question(text, fake_bot.username) == text
