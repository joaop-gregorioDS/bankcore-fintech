FROM python:3.12-slim

WORKDIR /opt/p6e
COPY scripts/p6e-financial-probe-requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt
COPY scripts/p6e-financial-probe.py ./p6e-financial-probe.py

ENTRYPOINT ["python", "/opt/p6e/p6e-financial-probe.py"]
