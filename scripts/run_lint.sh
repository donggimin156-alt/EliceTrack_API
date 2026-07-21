#!/usr/bin/env bash
# run_lint.sh — run_lint.bat 의 Linux/CI 버전
# Usage:
#   ./scripts/run_lint.sh        → CI 모드 (검사만, 코드 수정 없음)
#   ./scripts/run_lint.sh fix    → 로컬 모드 (format + check --fix, bat 와 동일)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="${1:-ci}"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck source=/dev/null
  source .venv/bin/activate
fi

echo "====================================================="
echo "Enterprise QA Framework - Ruff Linter & Formatter"
echo "====================================================="

if [[ "$MODE" == "fix" ]]; then
  echo "[INFO] 1. Running Ruff Formatter (write)..."
  python -m ruff format .
  echo "[INFO] 2. Running Ruff Linter (auto-fix)..."
  python -m ruff check . --fix
else
  echo "[INFO] 1. Ruff format --check (CI)..."
  python -m ruff format --check .
  echo "[INFO] 2. Ruff check (CI, no --fix)..."
  python -m ruff check .
fi

echo "====================================================="
echo "Linting completed!"
echo "====================================================="
