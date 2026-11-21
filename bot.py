"""
Hosted Telegram group bot — Python + python-telegram-bot + OpenAI.

Built for Fares: a friends group chat, Arabic-first.
  * Private chat: answers every text message, in Arabic.
  * Group: answers ONLY when mentioned (@botname), when someone
    replies to one of its messages, or when someone uses /ask.
    It never answers ordinary group chatter on its own.
    That is RESPOND_MODE=mention_only — the default.
  * Replies are always in Arabic: Egyptian dialect when the
    user writes in Egyptian dialect, Modern Standard Arabic
    when they write in Fusha.

Env vars (set them on your host, never commit them):
  TELEGRAM_BOT_TOKEN   required, from @BotFather /newbot
  OPENAI_API_KEY       required for AI answers; without it the bot
                       replies that the AI key is missing
  OPENAI_MODEL         default: gpt-4o-mini
  SYSTEM_PROMPT        default: Arabic friends-group prompt below
  RESPOND_MODE         mention_only | all | commands_only
                       default: mention_only — keep this for
                       a friends group, so the bot stays quiet
                       unless someone talks to it
  ALLOWED_CHAT_IDS     optional, comma-separated chat ids.
                       If set, the bot ignores every other chat.
  MAX_HISTORY          default: 10 messages kept per chat
"""

import logging
import os
import re
from collections import defaultdict, deque

from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("telegram-group-bot")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()
SYSTEM_PROMPT = os.environ.get(
    "SYSTEM_PROMPT",
    "أنت مساعد ودود في مجموعة تيليجرام مع أصدقاء. "
    "رد دائماً بالعربية. إذا كتب المستخدم باللهجة المصرية، رد باللهجة "
    "المصرية الودودة والطبيعية، وإذا كتب بالفصحى رد بالفصحى. "
    "كن مختصراً وطبيعياً وكأنك صديق في المجموعة، ولا تطل في الرد إلا "
    "إذا طلب منك ذلك. إذا لم تعرف شيئاً، قل ذلك بصراحة.",
).strip()
RESPOND_MODE = os.environ.get("RESPOND_MODE", "mention_only").strip().lower()
ALLOWED_CHAT_IDS = {
    int(x) for x in os.environ.get("ALLOWED_CHAT_IDS", "").split(",") if x.strip()
}
MAX_HISTORY = int(os.environ.get("MAX_HISTORY", "10"))

if RESPOND_MODE not in {"mention_only", "all", "commands_only"}:
    log.warning("Unknown RESPOND_MODE %r, falling back to mention_only", RESPOND_MODE)
    RESPOND_MODE = "mention_only"

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Short per-chat history: chat_id -> deque of {"role": ..., "content": ...}
history: dict[int, deque] = defaultdict(lambda: deque(maxlen=MAX_HISTORY * 2))


def is_allowed(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    chat = update.effective_chat
    return chat is not None and chat.id in ALLOWED_CHAT_IDS


def clean_question(text: str, bot_username: str | None) -> str:
    """Strip @botname mentions and /ask commands from the text."""
    text = text.strip()
    if bot_username:
        text = re.sub(rf"@{re.escape(bot_username)}\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^/ask(@\w+)?\s*", "", text)
    text = re.sub(r"^/start(@\w+)?\s*", "", text)
    return text.strip()


async def ask_llm(chat_id: int, question: str) -> str:
    if openai_client is None:
        return (
            "أنا شغال، بس مفتاح الذكاء الاصطناعي لسه مش متظبط. "
            "حط OPENAI_API_KEY على السيرفر وأعد تشغيلي."
        )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history[chat_id])
    messages.append({"role": "user", "content": question})

    try:
        resp = await openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,  # type: ignore[arg-type]
            temperature=0.7,
            max_tokens=800,
        )
        answer = (resp.choices[0].message.content or "").strip()
        if not answer:
            return "معلش، وصلني رد فاضي. جرّب تسأل تاني."
        history[chat_id].append({"role": "user", "content": question})
        history[chat_id].append({"role": "assistant", "content": answer})
        return answer
    except Exception as exc:  # keep the bot alive on API errors
        log.exception("OpenAI error: %s", exc)
        return "معلش، حصلت مشكلة وأنا بكلم الذكاء الاصطناعي. جرّب تاني بعد شوية."


def split_long(text: str, limit: int = 4000) -> list[str]:
    """Telegram caps messages at 4096 chars; split on paragraph breaks,
    hard-slicing any single paragraph that is still too long.
    Works the same for Arabic text — it splits on characters, not words."""
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    current = ""
    for chunk in text.split("\n\n"):
        # Hard-slice an over-long paragraph, flushing the buffer first.
        while len(chunk) > limit:
            if current:
                parts.append(current)
                current = ""
            parts.append(chunk[:limit])
            chunk = chunk[limit:]
        if not chunk:
            continue
        candidate = f"{current}\n\n{chunk}" if current else chunk
        if len(candidate) > limit:
            if current:
                parts.append(current)
            current = chunk
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts


async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE, question: str):
    question = question.strip()
    if not question:
        return
    chat = update.effective_chat
    assert chat is not None
    await context.bot.send_chat_action(chat_id=chat.id, action="typing")
    answer = await ask_llm(chat.id, question)
    message = update.effective_message
    assert message is not None
    for part in split_long(answer):
        await message.reply_text(part)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    chat = update.effective_chat
    assert chat is not None
    if chat.type in {"group", "supergroup"}:
        text = (
            "أهلاً! أنا موجود هنا.\n"
            "اعملي منشن (@"
            + (context.bot.username or "me")
            + ") أو استخدم /ask <سؤالك> وأنا أرد عليك.\n"
            "اكتب /help عشان تشوف اللي أقدر أعمله."
        )
    else:
        text = (
            "أهلاً! ابعتلي أي رسالة وأنا أرد عليك بالعربي.\n"
            "تقدر تستخدم /ask <سؤالك> أو تكتب عادي.\n"
            "اكتب /help عشان تشوف الأوامر، و /reset عشان تمسح تاريخ المحادثة."
        )
    await update.effective_message.reply_text(text)  # type: ignore[union-attr]


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    await update.effective_message.reply_text(  # type: ignore[union-attr]
        "الأوامر:\n"
        "/ask <سؤال> — اسألني أي حاجة\n"
        "/reset — امسح تاريخ المحادثة في الشات ده\n"
        "/help — اعرض المساعدة دي\n\n"
        "في المجموعة برد بس لما تعملي منشن، "
        "أو ترد على واحدة من رسايلي، أو تستخدم /ask."
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    chat = update.effective_chat
    assert chat is not None
    history[chat.id].clear()
    await update.effective_message.reply_text("تمام — مسحت تاريخ المحادثة في الشات ده.")  # type: ignore[union-attr]


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    message = update.effective_message
    assert message is not None
    question = clean_question(message.text or "", context.bot.username)
    if not question:
        await message.reply_text("اسألني كده: /ask عاصمة مصر إيه؟")
        return
    await reply(update, context, question)


async def on_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    message = update.effective_message
    if message is None or not message.text:
        return
    # Never reply to other bots, and never reply to ourselves.
    sender = message.from_user
    if sender is None or sender.is_bot:
        return

    chat = update.effective_chat
    assert chat is not None

    # Private chats: answer everything.
    if chat.type == "private":
        await reply(update, context, message.text)
        return

    # Groups: mention / reply only, unless RESPOND_MODE says otherwise.
    if RESPOND_MODE == "commands_only":
        return

    bot_username = context.bot.username
    mentioned = bool(bot_username) and f"@{bot_username.lower()}" in message.text.lower()
    replied_to_bot = bool(
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == context.bot.id
    )

    if RESPOND_MODE == "all":
        await reply(update, context, message.text)
    elif mentioned or replied_to_bot:
        question = clean_question(message.text, bot_username)
        if question:
            await reply(update, context, question)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.exception("Update %s failed: %s", update, context.error)


def register_handlers(app):
    app.add_handler(CommandHandler("start", start, filters=filters.UpdateType.MESSAGE))
    app.add_handler(CommandHandler("help", help_command, filters=filters.UpdateType.MESSAGE))
    app.add_handler(CommandHandler("ask", ask_command, filters=filters.UpdateType.MESSAGE))
    app.add_handler(CommandHandler("reset", reset, filters=filters.UpdateType.MESSAGE))
    app.add_handler(
        MessageHandler(
            filters.UpdateType.MESSAGE & filters.TEXT & ~filters.COMMAND,
            on_group_message,
        )
    )
    app.add_error_handler(on_error)


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN is not set. "
            "Create a bot with @BotFather, then set the token as an env var."
        )
    log.info("Starting bot, respond_mode=%s model=%s", RESPOND_MODE, OPENAI_MODEL)
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    register_handlers(app)
    # Polling is simplest for a hosted worker: no domain / webhook needed.
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
