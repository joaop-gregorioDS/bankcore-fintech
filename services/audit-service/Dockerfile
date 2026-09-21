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
      org.opencontainers.image.title="BankCore Audit Consumer"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system --gid 10001 bankcore && \
    useradd --system --uid 10001 --gid bankcore --home-dir /nonexistent \
        --shell /usr/sbin/nologin bankcore

COPY services/audit-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

COPY --chown=bankcore:bankcore services/audit-service/audit_app ./audit_app
COPY --chown=bankcore:bankcore common ./common
COPY --chown=bankcore:bankcore infra/postgres/alembic/audit ./alembic/audit
COPY --chown=bankcore:bankcore infra/postgres/migrate_audit.py ./migrate_audit.py

USER bankcore

CMD ["python", "-m", "audit_app.consumer"]
