#!/usr/bin/env bash
# run_tests.sh — run_tests.bat 의 Linux/CI 버전 (프로젝트 루트 기준)
# Usage:
#   ./scripts/run_tests.sh [pytest_env] [marker]
#   pytest_env: --env 값 (기본 qa)
#   marker: smoke | api | (비우면 tests/ 전체)
#
# TARGET(dev/prod)은 호출 전 export TARGET=... 로 설정 (Jenkinsfile에서 주입)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTEST_ENV="${1:-qa}"
MARKER="${2:-}"

echo "====================================================="
echo "Enterprise QA Automation Framework Execution"
echo "====================================================="

echo "[INFO] Cleaning up previous test results..."
rm -rf reports/allure-results reports/allure-report
find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find . -type d -name .pytest_cache -prune -exec rm -rf {} + 2>/dev/null || true
mkdir -p reports

if [[ -f .venv/bin/activate ]]; then
  # shellcheck source=/dev/null
  source .venv/bin/activate
fi

COMMON=(
  -v
  "--env=${PYTEST_ENV}"
  --alluredir=reports/allure-results
  --junitxml=reports/junit.xml
)

run_pytest() {
  if [[ -z "$MARKER" ]]; then
    echo "[INFO] Target: ALL tests/ | pytest --env=${PYTEST_ENV} | TARGET=${TARGET:-dev}"
    python -m pytest tests/ -n auto "${COMMON[@]}"
  elif [[ "$MARKER" == "api" ]]; then
    echo "[INFO] Target: tests/api/ (-m api) | pytest --env=${PYTEST_ENV}"
    python -m pytest tests/api/ -m api -n auto "${COMMON[@]}"
  else
    echo "[INFO] Target: MARKER '${MARKER}' | pytest --env=${PYTEST_ENV}"
    python -m pytest tests/ -m "$MARKER" -n auto "${COMMON[@]}"
  fi
}

run_pytest

echo "====================================================="
echo "Generating Allure Report (HTML, no serve in CI)"
echo "====================================================="
if command -v allure >/dev/null 2>&1; then
  allure generate reports/allure-results -o reports/allure-report --clean
else
  echo "[WARN] allure CLI not in PATH — skip generate (Jenkins Allure Plugin may still publish results)"
fi
