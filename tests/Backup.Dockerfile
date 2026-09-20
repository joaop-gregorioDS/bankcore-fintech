FROM postgres:16.4-alpine3.20

RUN apk add --no-cache python3 py3-pip && \
    pip install --no-cache-dir --break-system-packages \
        asyncpg==0.29.0 bcrypt==4.0.1

WORKDIR /workspace
COPY scripts/backup_restore.py /workspace/backup_restore.py

USER postgres
ENTRYPOINT ["python3", "/workspace/backup_restore.py"]
