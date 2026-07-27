#!/usr/bin/env bash
# nginx Allure HTML 배포
# - latest: /var/www/allure/<branch>/latest/  (항상 최신 1개)
# - build:  /var/www/allure/<branch>/<BUILD_NUMBER>/  (빌드별 고정 — Slack 링크용)
#
# Usage:
#   BRANCH=develop ALLURE_PUBLIC_ROOT=/var/www/allure ./scripts/publish_allure_latest.sh
#   BRANCH=develop BUILD_NUMBER=123 ./scripts/publish_allure_latest.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BRANCH="${BRANCH:?set BRANCH (develop|main)}"
ALLURE_PUBLIC_ROOT="${ALLURE_PUBLIC_ROOT:-/var/www/allure}"
BUILD_NUMBER="${BUILD_NUMBER:-}"

if ! command -v allure >/dev/null 2>&1; then
  echo "[ERROR] allure CLI not found"
  exit 1
fi

allure generate reports/allure-results -o reports/allure-report --clean

publish_dir() {
  local dest="$1"
  mkdir -p "$dest"
  cp -a reports/allure-report/. "$dest/"
  echo "[INFO] Published to ${dest}"
}

publish_dir "${ALLURE_PUBLIC_ROOT}/${BRANCH}/latest"

if [[ -n "$BUILD_NUMBER" ]]; then
  publish_dir "${ALLURE_PUBLIC_ROOT}/${BRANCH}/${BUILD_NUMBER}"
fi
