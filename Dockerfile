FROM python:3.13-slim

# System deps for WeasyPrint (pango, cairo, gdk-pixbuf) and Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libglib2.0-0 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY alembic.ini ./
COPY alembic/ alembic/
COPY app/ app/
COPY scripts/ scripts/
COPY main.py export_schema.py ./

RUN chmod +x scripts/entrypoint.sh

EXPOSE 8000

CMD ["scripts/entrypoint.sh"]
