FROM python:3.12.8-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd --system --gid 10001 bankcore && \
    useradd --system --uid 10001 --gid bankcore --home-dir /nonexistent \
        --shell /usr/sbin/nologin bankcore && \
    chown -R bankcore:bankcore /app

COPY services/transactions-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

COPY --chown=bankcore:bankcore services/transactions-service/app ./app
COPY --chown=bankcore:bankcore infra/postgres/alembic/transactions ./alembic/transactions
COPY --chown=bankcore:bankcore infra/postgres/preflight.py ./preflight.py
COPY --chown=bankcore:bankcore infra/postgres/migrate.py ./migrate.py

USER bankcore
EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
