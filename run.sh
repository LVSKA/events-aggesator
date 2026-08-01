#!/bin/bash
set -e

export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

uv run ./manage.py migrate
uv run ./manage.py collectstatic --noinput

uv run python -m celery -A core worker -P solo -B -l INFO &
uv run python -m gunicorn -b 0.0.0.0:8000 --workers=1 --threads=8 \
  --worker-class=gthread --timeout 120 --preload core.wsgi:application &
wait
