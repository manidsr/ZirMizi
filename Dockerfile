FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot ./bot

# SQLite lives on a volume so data survives container restarts.
RUN useradd --create-home appuser && mkdir /data && chown appuser /data
ENV DATABASE_URL=sqlite+aiosqlite:////data/bot.db
VOLUME /data
USER appuser

CMD ["python", "-m", "bot"]
