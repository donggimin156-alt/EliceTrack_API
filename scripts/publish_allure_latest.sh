#!/usr/bin/env bash
# nginx 고정 URL(/var/www/allure/<branch>/latest/) 로 Allure HTML 배포
# Usage: BRANCH=develop ALLURE_PUBLIC_ROOT=/var/www/allure ./scripts/publish_allure_latest.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BRANCH="${BRANCH:?set BRANCH (develop|main)}"
ALLURE_PUBLIC_ROOT="${ALLURE_PUBLIC_ROOT:-/var/www/allure}"
DEST="${ALLURE_PUBLIC_ROOT}/${BRANCH}/latest"

if ! command -v allure >/dev/null 2>&1; then
  echo "[ERROR] allure CLI not found"
  exit 1
fi

allure generate reports/allure-results -o reports/allure-report --clean
mkdir -p "$DEST"
cp -a reports/allure-report/. "$DEST/"
echo "[INFO] Published to ${DEST}"
