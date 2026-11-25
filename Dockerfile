# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    LOG_LEVEL=info \
    MAX_TOOL_TURNS=110

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a non-root account.
RUN useradd --create-home --uid 10001 harness \
    && chown -R harness:harness /app
USER 10001:10001

EXPOSE 8000
CMD ["python", "serve.py"]
