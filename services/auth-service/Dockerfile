ARG OCI_SOURCE="https://github.com/joaop-gregorioDS/bankcore-fintech"
ARG OCI_REVISION="unknown"
ARG OCI_VERSION="dev"

FROM python:3.12.8-slim-bookworm

ARG OCI_SOURCE
ARG OCI_REVISION
ARG OCI_VERSION

LABEL org.opencontainers.image.source="${OCI_SOURCE}" \
      org.opencontainers.image.revision="${OCI_REVISION}" \
      org.opencontainers.image.version="${OCI_VERSION}" \
      org.opencontainers.image.title="BankCore Auth Service"

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

COPY services/auth-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

COPY --chown=bankcore:bankcore services/auth-service/app ./app
COPY --chown=bankcore:bankcore common ./common
COPY --chown=bankcore:bankcore infra/postgres/alembic/auth ./alembic/auth
COPY --chown=bankcore:bankcore infra/postgres/preflight.py ./preflight.py
COPY --chown=bankcore:bankcore infra/postgres/migrate.py ./migrate.py

USER bankcore
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
