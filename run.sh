#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
export GDK_BACKEND=x11
exec .venv/bin/python -m overlay "$@"
