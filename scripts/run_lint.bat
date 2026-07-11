:: run_lint.bat
@echo off
chcp 65001 > nul
echo =====================================================
echo 🧹 Enterprise QA Framework - Ruff Linter ^& Formatter
echo =====================================================

:: 1. Formatter 실행: pyproject.toml 정책에 따라 띄어쓰기, 줄바꿈, 따옴표 자동 통일
echo [INFO] 1. Running Ruff Formatter...
python -m ruff format .
echo.

:: 2. Linter 실행: 사용하지 않는 변수/Import 제거 및 Import 그룹별 순서 자동 정렬 (--fix)
echo [INFO] 2. Running Ruff Linter (Auto-fixing)...
python -m ruff check . --fix
echo.

echo =====================================================
echo ✅ Linting and Formatting completed!
echo =====================================================