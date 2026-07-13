:: run_tests.bat
@echo off
chcp 65001 > nul
echo =====================================================
echo 🚀 Enterprise QA Automation Framework Execution
echo =====================================================

:: 1. 이전 테스트 결과 및 파이썬 캐시 정리 (Clean up)
echo [INFO] Cleaning up previous test results...
if exist "reports\allure-results" rmdir /s /q "reports\allure-results"
if exist "reports\allure-report" rmdir /s /q "reports\allure-report"
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
for /d /r . %%d in (.pytest_cache) do @if exist "%%d" rd /s /q "%%d"

:: 2. 환경 변수 및 실행 마커 세팅
set ENV=%~1
if "%ENV%"=="" set ENV=qa

set MARKER=%~2
set TEST_ENV=%ENV%

:: 3. 테스트 실행 (pytest.ini에서 제외한 동적 실행 옵션 주입)
:: 병렬 워커(-n auto)와 리포트 경로(--alluredir)는 CI/CD 환경이나 로컬 환경에 따라 
:: 유연하게 변동될 수 있으므로 설정 파일이 아닌 실행 스크립트(배치 파일)에서 제어합니다.
if "%MARKER%"=="" (
    echo [INFO] Target: ALL Tests ^| Environment: %ENV%
    python -m pytest tests/ -n auto --alluredir=reports\allure-results
) else (
    echo [INFO] Target: MARKER '%MARKER%' ^| Environment: %ENV%
    python -m pytest tests/ -m "%MARKER%" -n auto --alluredir=reports\allure-results
)

:: 4. Allure Report 생성 및 로컬 웹 서버 실행
echo =====================================================
echo 📊 Generating and Serving Allure Report...
echo =====================================================
call allure generate reports\allure-results -o reports\allure-report --clean
call allure serve reports\allure-results