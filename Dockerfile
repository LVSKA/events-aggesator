FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

COPY . .

RUN chmod +x run.sh

EXPOSE 8000
RUN chown -R 1000:1000 /app
USER 1000
CMD ["bash", "./run.sh"]
