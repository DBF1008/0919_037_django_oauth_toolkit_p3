#!/bin/sh
# Run all lint, migration and unit test checks for this project.
# Mirrors the tox "lite3" environments: lint, migrations-dj*-lite3,
# scenario-migrate-swapped and the pytest unit test suite.
set -e

cd "$(dirname "$0")"

PYTHON=".venv/bin/python"
if [ ! -x "$PYTHON" ]; then
    PYTHON="python3"
fi

RUFF=".venv/bin/ruff"
if [ ! -x "$RUFF" ]; then
    RUFF="ruff"
fi

export PYTHONPATH=.
export PYTHONWARNINGS=all

echo "==> ruff format --check"
"$RUFF" format --check

echo "==> ruff check"
"$RUFF" check

echo "==> makemigrations --dry-run --check (tests.mig_settings)"
DJANGO_SETTINGS_MODULE=tests.mig_settings "$PYTHON" -m django makemigrations --dry-run --check

echo "==> migrate with swapped models (tests.settings_swapped)"
DJANGO_SETTINGS_MODULE=tests.settings_swapped "$PYTHON" -m django migrate

echo "==> pytest unit tests (tests.settings)"
DJANGO_SETTINGS_MODULE=tests.settings "$PYTHON" -m pytest tests -q

echo "==> all checks passed"
