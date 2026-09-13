FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps: psycopg2 needs pg_config, pypdf/reportlab are pure-python.
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

EXPOSE 8000

# Default: the FastAPI server. Override for MCP servers:
#   docker run ... placepilot-backend python -m app.mcp.run placement
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
