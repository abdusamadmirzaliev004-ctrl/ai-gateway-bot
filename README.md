# AI Gateway Bot

A Telegram bot that unifies many AI providers behind one clean menu UI.

## Providers + models (32 total)

| Provider          | Models                                                                                                      |
|-------------------|-------------------------------------------------------------------------------------------------------------|
| GitHub Copilot Pro+ | claude-opus-4.7, sonnet-4.6/4.5, opus-4.5, haiku-4.5, gpt-5.5/5.4/5.4-mini/5.3-codex/5.2/4.1, grok-code-fast-1, gemini-3.1-pro-preview, gemini-2.5-pro |
| OpenAI            | gpt-4o, gpt-4o-mini, o1-mini, gpt-4-turbo                                                                   |
| Anthropic         | claude-3.5-sonnet, claude-3.5-haiku, claude-3-opus                                                          |
| Google Gemini     | gemini-1.5-pro, gemini-1.5-flash                                                                            |
| xAI Grok          | grok-2-latest, grok-2-mini                                                                                  |
| DeepSeek          | V3 (deepseek-chat), R1 (deepseek-reasoner)                                                                  |
| OpenRouter        | auto-router + curated set: Claude 3.5 Sonnet, GPT-4o, Llama 3.3 70B, Mistral Large, DeepSeek R1, Qwen 2.5 72B, Gemini 1.5 Pro |

Add more OpenRouter models in `providers/catalog.py`.

## Features

- Inline-keyboard navigation, Apple-flat menu
- Models grouped by provider, each with description + tag chips
- Last-used model remembered **per provider** per user
- Modes: Fast / Smart / Creative — Styles: Short / Detailed
- Conversation memory toggle, regenerate, clear chat
- Per-user daily message + token quotas, sliding-window rate limit
- Admin panel: `/stats`, `/users`, `/ban`, `/unban`, `/setlimit`
- Provider fallback chain (configurable)
- SQLite by default, Postgres ready (just change `DATABASE_URL`)
- Webhook (production) or long-polling (dev) — auto-detected from `WEBHOOK_URL`
- `/health` endpoint
- Docker, Railway, Fly.io, Render, systemd configs included

## Project layout

```
bot/         handlers, keyboards, texts
providers/   abstraction + 7 providers + model catalog
services/    DB repo + quota service
database/    SQLAlchemy models + async engine
config/      pydantic-settings
deploy/      systemd unit + nginx snippet
main.py      aiohttp webhook / polling entrypoint
```

## Local dev

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # fill BOT_TOKEN + at least one provider key
python main.py             # long-polling mode
```

## Production: Railway (24/7 webhook)

Railway is the fastest path.

1. **Push to GitHub**
   ```bash
   cd ~/ai-gateway-bot
   git remote add origin git@github.com:YOUR_USER/ai-gateway-bot.git
   git push -u origin main
   ```

2. **Create Railway project**
   - https://railway.app → New Project → Deploy from GitHub Repo → pick this repo.
   - Railway auto-detects `Dockerfile` and `railway.json`.

3. **Add a Postgres plugin** (optional but recommended):
   - In the project → New → Database → Postgres.
   - Copy the `DATABASE_URL` Railway gives you and convert the prefix:
     `postgres://...`  →  `postgresql+asyncpg://...`

4. **Set environment variables** (Project → Variables):
   ```
   BOT_TOKEN              = <from @BotFather>
   GITHUB_COPILOT_TOKEN   = <your Copilot bearer token>
   OPENAI_API_KEY         = sk-...           (optional)
   ANTHROPIC_API_KEY      = sk-ant-...       (optional)
   GOOGLE_API_KEY         = AIza...          (optional)
   XAI_API_KEY            = xai-...          (optional)
   DEEPSEEK_API_KEY       = sk-...           (optional)
   OPENROUTER_API_KEY     = sk-or-...        (optional)
   ADMIN_IDS              = <your TG user id>
   DEFAULT_PROVIDER       = github_copilot
   FALLBACK_CHAIN         = github_copilot,openai,anthropic
   DATABASE_URL           = <from Postgres plugin, asyncpg form>
   WEBHOOK_SECRET         = <random 32+ char string>
   WEBAPP_PORT            = 8080
   ```

5. **Generate a public domain** (Settings → Networking → Generate Domain).
   Copy it, then set:
   ```
   WEBHOOK_URL = https://<your-app>.up.railway.app
   ```

6. **Redeploy.** The bot will:
   - Detect `WEBHOOK_URL` is set → run aiohttp in webhook mode.
   - Self-register the webhook with Telegram on startup.
   - Expose `/health` for Railway health-checks.
   - Run 24/7 (Railway keeps web services alive).

7. **Verify**:
   - Open `https://<your-app>.up.railway.app/health` → `{"ok": true}`.
   - DM the bot `/start` on Telegram.

### Telegram webhook details

- The bot calls `bot.set_webhook(...)` automatically using `WEBHOOK_URL + WEBHOOK_PATH`.
- Telegram requires HTTPS — Railway domains are HTTPS by default.
- `WEBHOOK_SECRET` is sent as the `X-Telegram-Bot-Api-Secret-Token` header and validated.

### Other targets

- **Fly.io**: `fly launch` (uses `fly.toml`), then `fly secrets set ...`.
- **Render**: connect repo, uses `render.yaml`.
- **VPS**: copy `deploy/ai-gateway-bot.service`, `systemctl enable --now`. Front with `deploy/nginx.conf`.
- **Docker**: `docker compose up -d`.

## Admin commands

- `/admin` — show panel
- `/stats` — global counts
- `/users` — recent active users
- `/ban <id>` / `/unban <id>`
- `/setlimit <id> <messages> <tokens>`

## Adding more models

Edit `providers/catalog.py` and append `Model(...)` rows. The UI picks them up automatically — no code changes needed elsewhere.

## License

MIT
