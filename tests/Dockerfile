FROM python:3.12.8-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace

RUN groupadd --system --gid 10001 bankcore && \
    useradd --system --uid 10001 --gid bankcore --home-dir /nonexistent \
        --shell /usr/sbin/nologin bankcore

COPY services/auth-service/requirements.txt /tmp/auth-requirements.txt
COPY services/transactions-service/requirements.txt /tmp/transactions-requirements.txt
COPY services/audit-service/requirements.txt /tmp/audit-requirements.txt
RUN pip install --no-cache-dir --disable-pip-version-check \
    -r /tmp/auth-requirements.txt \
    -r /tmp/transactions-requirements.txt \
    -r /tmp/audit-requirements.txt \
    pytest==8.3.3

COPY --chown=bankcore:bankcore services ./services
COPY --chown=bankcore:bankcore infra ./infra
COPY --chown=bankcore:bankcore docs ./docs
COPY --chown=bankcore:bankcore tests ./tests
COPY --chown=bankcore:bankcore scripts ./scripts
COPY --chown=bankcore:bankcore pytest.ini conftest.py ./
COPY --chown=bankcore:bankcore docker-compose.yml docker-compose.test.yml ./

RUN chown -R bankcore:bankcore /workspace

USER bankcore

CMD ["python", "scripts/run_tests.py"]
