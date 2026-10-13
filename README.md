# Telegram Bot

A small, scalable Telegram bot built on [aiogram 3](https://docs.aiogram.dev/) and SQLAlchemy 2 (async).

What it does now:
- `/start` shows a Farsi welcome message with a **ثبت‌نام** (sign up) button
- Sign up asks for first name and last name, then saves the user in the database
- Registered users get a main menu: خرید غذا / فروش غذا / کیف پول / حساب کاربری

## Run locally

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Set it up (run these from the project root, the folder that contains `bot/`):

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env             # Windows: copy .env.example .env
   # put your token in .env
   python run.py
   ```
3. Open your bot in Telegram and send `/start`.

The SQLite database is created automatically as `bot.db` in the project root.

## Run with Docker

```bash
docker build -t telegram-bot .
docker run --rm --env-file .env -v bot-data:/data telegram-bot
```

## Project layout

```
run.py               entry point (same as python -m bot)
bot/
  main.py            builds Bot + Dispatcher + DB and starts polling
  config.py          typed settings from env / .env
  db/
    models.py        ORM models (User)
    session.py       engine, session factory, table creation
    repositories/    all queries, one class per entity
  handlers/          one router per feature (start, signup, menu)
  keyboards/         reply / inline keyboards
  middlewares/       DB session + current user, "must be registered" guard
  texts/             all user-facing text, one catalog per language
```

## Adding things later

- **New menu button:** add its text in `texts/fa.py`, put it in `keyboards/main_menu.py`, add a handler in `handlers/menu.py`.
- **New feature:** add `handlers/<feature>.py` with a `router`, include it in `handlers/__init__.py`.
- **New table:** add a model in `db/models.py` and a repository in `db/repositories/`.
- **PostgreSQL:** `pip install asyncpg`, then set `DATABASE_URL=postgresql+asyncpg://user:pass@host/db`. No code changes.
- **Changing columns on a live database:** adopt [Alembic](https://alembic.sqlalchemy.org/) migrations. Until then, tables are only created, never altered.
- **Multiple bot instances:** switch the FSM storage in `main.py` from memory to Redis.
- **Another language:** add `texts/en.py` with the same keys and register it in `texts/__init__.py`.
