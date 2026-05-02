# AI Gateway — Telegram Bot

A production-ready Telegram bot that acts as a unified gateway to multiple AI
providers (OpenAI / Anthropic / Microsoft Copilot) with per-user tracking,
quotas, modes, conversation memory, an admin panel, and webhook deployment.

## Features
- Inline-keyboard, menu-driven UI (Apple-like minimal)
- Multi-provider abstraction: `generate_response(prompt, provider, model, settings)`
- Modes: `fast` / `smart` / `creative` · Styles: `short` / `detailed`
- Conversation memory (per-user, toggleable), regenerate & clear
- Per-user daily message + token quotas, sliding-window rate limit
- Provider fallback chain on failures
- Admin panel: `/admin`, `/stats`, `/users`, `/ban`, `/unban`, `/setlimit`
- Async SQLAlchemy 2.0 (SQLite for dev, Postgres for prod)
- Webhook (production) and long-polling (dev) modes
- Dockerfile + Compose, Fly.io, Railway, Render, systemd configs

## Project layout
```
bot/             # Telegram handlers, keyboards, copy
providers/       # Provider abstraction + openai / anthropic / copilot impls
services/        # repo (CRUD), limits (quota + rate limiting)
database/        # SQLAlchemy models + engine
config/          # pydantic settings (.env)
deploy/          # systemd + nginx samples
main.py          # Webhook + polling entrypoint
```

## Quick start (local, polling)
```
cp .env.example .env          # fill in BOT_TOKEN + at least one provider key
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```
Leave `WEBHOOK_URL` empty in `.env` to use long-polling for development.

## Production deploy

### Docker / VPS
```
docker compose up -d --build
```
Then point Telegram at your public HTTPS URL by setting `WEBHOOK_URL` in `.env`.

### VPS (systemd + nginx)
1. Place repo at `/opt/ai-gateway-bot`, create `.venv`, `pip install -r requirements.txt`.
2. `sudo cp deploy/ai-gateway-bot.service /etc/systemd/system/` then `systemctl enable --now ai-gateway-bot`.
3. Configure nginx using `deploy/nginx.conf` and obtain a Let's Encrypt cert.

### Railway / Render / Fly.io
- Railway: `railway up` (uses `railway.json` + Dockerfile). Set env vars in dashboard.
- Render: connect repo; `render.yaml` is auto-detected.
- Fly: `fly launch --copy-config --no-deploy`, `fly secrets set BOT_TOKEN=...`, `fly deploy`.

In every case set `WEBHOOK_URL` to the platform-provided HTTPS hostname.

## Adding a new provider
1. Create `providers/myprovider_provider.py` subclassing `BaseProvider`.
2. Register it in `providers/__init__.py` (`get_provider` and `AVAILABLE_PROVIDERS`).
3. Map `model_map = {"fast": "...", "smart": "...", "creative": "..."}`.
That's it — UI, fallback, quotas, and history all work automatically.

## Admin
Add your Telegram numeric ID to `ADMIN_IDS` in `.env`. Then DM `/admin`.

## Notes on Microsoft Copilot
There is no general public Copilot Chat API. The included `copilot_provider.py`
targets two compatible endpoints via env vars:
- **Azure OpenAI** deployment URL (recommended), or
- **GitHub Copilot Chat API** (partner-only).
If neither is configured, the gateway transparently falls back to the next
provider in `FALLBACK_CHAIN`.

## Security
- API keys live in env vars only. Never commit `.env`.
- Webhook is protected by `WEBHOOK_SECRET` (Telegram sends it as a header).
- Per-user rate limit + ban list to mitigate abuse.
