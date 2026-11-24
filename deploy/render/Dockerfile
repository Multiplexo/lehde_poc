# All-in-one image for a free Render web service: web UI (nginx), API and the
# in-process analysis. Build context is the repository root.

FROM oven/bun:1.4 AS frontend
WORKDIR /app
COPY frontend/package.json frontend/bun.lock ./
RUN bun install --frozen-lockfile
COPY frontend/ ./
ARG VITE_CUSTOMER_NAME=Lehde
ENV VITE_CUSTOMER_NAME=$VITE_CUSTOMER_NAME
RUN bun run build

FROM ghcr.io/astral-sh/uv:0.11 AS uv

FROM python:3.13-slim
# Tesseract with German data for scans, nginx for UI and password protection,
# openssl to hash the demo password at start.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        nginx openssl tesseract-ocr tesseract-ocr-deu \
    && rm -rf /var/lib/apt/lists/* /etc/nginx/sites-enabled/default
COPY --from=uv /uv /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1 \
    STORAGE_BACKEND=database LOG_FORMAT=json
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --locked --no-dev --no-install-project
COPY backend/app ./app
COPY backend/alembic.ini ./
COPY backend/alembic ./alembic

COPY --from=frontend /app/dist /app/frontend
COPY deploy/render/nginx.conf /etc/nginx/conf.d/app.conf
COPY deploy/render/start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 10000
CMD ["/app/start.sh"]
