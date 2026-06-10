FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LAW_DATA_DIR=/app/legislation \
    LOG_DIR=/app/log/long-batch

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir "setuptools>=69" wheel \
    && pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml README.md ./
COPY domain ./domain
COPY shell ./shell
COPY ops ./ops

RUN pip install --no-cache-dir --no-build-isolation --no-deps --force-reinstall . \
    && chmod +x /app/shell/*.sh \
    && mkdir -p /app/legislation /app/log/long-batch

VOLUME ["/app/legislation", "/app/log/long-batch"]

CMD ["tail", "-f", "/dev/null"]
