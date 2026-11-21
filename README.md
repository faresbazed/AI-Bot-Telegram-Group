# Telegram Group Bot — hosted Python bot

A Python bot for a friends group chat on Telegram. It reads Arabic messages and answers in Arabic.

**Behaviour — mention / reply only:**
- Private chat: answers every message, in Arabic
- Group: answers **only** when someone @mentions it, replies to one of its messages, or uses `/ask <question>`
- It stays quiet for ordinary group chatter — good for a friends group, no spam
- `/start`, `/help`, `/reset` work in both
- Replies are always in Arabic: Egyptian dialect when the user writes in Egyptian dialect, Modern Standard Arabic when they write in Fusha

`RESPOND_MODE` is `mention_only` by default. Do not change it to `all` for this group unless you really want it answering everything.

## 1. Create the bot (5 minutes)

1. In Telegram, open **@BotFather** (check the blue verified tick, username exactly `@BotFather`)
2. Send `/newbot`, pick a display name and a username ending in `bot`
3. Copy the token BotFather sends you. **Keep it secret — never post it in a group, a screenshot, or a public repo.**
4. Add the bot to your group: group info → Add members → pick the bot.

Because this bot only answers mentions and replies, you do **not** need to turn privacy mode off, and you do **not** need to make it an admin. Privacy mode on (the default) is actually what you want: Telegram will only send it @mentions, commands, and replies to it.

The bot still only sees *new* messages — Telegram's Bot API cannot read chat history.

## 2. Get an LLM key

This version uses OpenAI. Get a key at https://platform.openai.com/api-keys

- Model default is `gpt-4o-mini` — cheap and fast for a group. Change `OPENAI_MODEL` if you want another model.
- Without `OPENAI_API_KEY`, the bot still starts, but tells users in Arabic that the AI key is missing.
- Arabic works fine with this model — no special setup is needed. The bot sends and receives Arabic text as normal UTF-8.

You can swap the `ask_llm()` function in `bot.py` for Anthropic / another provider later — the rest of the bot does not care which LLM answers.

## 3. Deploy it on Railway

1. Push this folder to GitHub.
2. Railway → New Project → **Deploy from GitHub** → pick the repo.
3. Railway detects Python (Nixpacks). `railway.json` and `Procfile` set the start command to `python bot.py`. If Railway asks, set the start command to `python bot.py` yourself.
4. In Railway → Variables, set:
   - `TELEGRAM_BOT_TOKEN` = your BotFather token
   - `OPENAI_API_KEY` = your OpenAI key
   - `OPENAI_MODEL` = `gpt-4o-mini`
   - `RESPOND_MODE` = `mention_only`
   - `SYSTEM_PROMPT` = the Arabic prompt from `.env.example` (optional — the default in `bot.py` is already Arabic)
5. Deploy. Check Logs — you should see `Starting bot, respond_mode=mention_only`.

Railway has no free tier that stays on forever for a worker like this in the same way it used to — expect a small paid plan (about $5/month) for a bot that must always be on. That is the trade-off for Railway's simplicity.

Other hosts are still in this folder if you change your mind: `render.yaml` for Render, `Dockerfile` + `fly.toml` for Fly.io.

### Local test

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in your real tokens in .env
# load it, e.g. with: set -a; source .env; set +a
python bot.py
```

Never commit `.env`. Only run **one** copy at a time — local or Railway, not both — or the bot will reply twice.

**Running tests:** `.venv/bin/pip install -r requirements-dev.txt && .venv/bin/python -m pytest` (offline; no tokens needed).

## 4. Test it in the group

1. Send `/start@your_bot_name` in the group — it should greet you in Arabic.
2. Send `@your_bot_name إزيك؟` — it should answer in Arabic.
3. Reply to one of its messages with a question — it should answer that too.
4. Send `/ask عاصمة مصر إيه؟` — it should answer.
5. Send an ordinary message with no mention — it should stay quiet. That is correct for `mention_only`.

## Customise it

Edit these in `bot.py` or via env vars:

- `SYSTEM_PROMPT` — personality and language. Default is already:
  > أنت مساعد ودود في مجموعة تيليجرام مع أصدقاء. رد دائماً بالعربية. إذا كتب المستخدم باللهجة المصرية، رد باللهجة المصرية الودودة والطبيعية، وإذا كتب بالفصحى رد بالفصحى…
- `RESPOND_MODE` — keep `mention_only` for a friends group. `all` = every group message (needs privacy mode off, or bot as admin). `commands_only` = only `/ask`.
- `ALLOWED_CHAT_IDS` — comma-separated Telegram chat ids. If set, the bot ignores every other chat. Useful to lock it to one group.
- `MAX_HISTORY` — how many recent messages per chat it remembers (default 10).

Want it more Egyptian, more formal, funnier, or shorter? Tell me and I will change the prompt — the code does not need to change.

## Costs to expect

- Telegram Bot API: free.
- OpenAI `gpt-4o-mini`: a few dollars a month for a small friends group, depending on volume. Check usage at platform.openai.com.
- Railway: a small paid plan for an always-on worker.

## Troubleshooting

- **Bot does nothing in the group:** send `@botname` or `/ask@botname` — those always get through. If even those do nothing, check Railway logs: is the bot running, and is `TELEGRAM_BOT_TOKEN` set correctly?
- **Bot answers in private but not in the group:** it was probably not added to the group, or you are sending ordinary messages with no mention — with `mention_only` that is supposed to stay quiet.
- **"مفتاح الذكاء الاصطناعي لسه مش متظبط":** `OPENAI_API_KEY` is missing or wrong on Railway. Set it in Variables and redeploy.
- **"TELEGRAM_BOT_TOKEN is not set":** the env var is missing on Railway. It must be set where the bot runs, not just locally.
- **Bot replies twice / old messages:** only one copy of the bot should be running. Stop the local test copy before deploying, or vice versa.
- **Arabic looks wrong / garbled:** it should not — Telegram and Python both use UTF-8. If you see garbled text, it is almost always the terminal or editor encoding, not the bot.

## Files

- `bot.py` — the bot (Arabic prompts, mention/reply only)
- `requirements.txt` — `python-telegram-bot`, `openai`
- `railway.json`, `Procfile` — Railway deploy
- `render.yaml` — Render Background Worker (alternative)
- `Dockerfile`, `fly.toml` — Fly.io / Docker deploy (alternative)
- `.env.example` — env vars to set (no real secrets in here)
