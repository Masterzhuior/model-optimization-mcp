FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MOMCP_HOME=/data \
    MOMCP_HOST=0.0.0.0 \
    MOMCP_PORT=8000

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["model-optimization-mcp", "http", "--host", "0.0.0.0", "--port", "8000"]

