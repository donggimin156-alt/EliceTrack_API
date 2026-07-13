# Dockerfile

# 1. 가볍고 안정적인 파이썬 공식 slim 이미지 사용
FROM python:3.11-slim

# 2. 파이썬 컨테이너 최적화 환경 변수
# .pyc 바이트코드를 쓰지 않고, 로그 버퍼링을 없애 실시간 CI/CD 로그 스트리밍 보장
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. OS 의존성 및 타임존(KST) 설정
# (테스트 시 인증/결제/데이터 검증에 시간 동기화가 매우 중요함)
RUN apt-get update && apt-get install -y tzdata curl \
    && rm -rf /var/lib/apt/lists/*
ENV TZ=Asia/Seoul

# 4. 보안을 위한 Non-root 유저 생성 (엔터프라이즈 보안 표준)
# root 권한으로 테스트를 실행하여 발생할 수 있는 컨테이너 취약점을 방어합니다.
RUN useradd -m qa_user

# 5. 작업 디렉터리 설정
WORKDIR /app

# 6. 의존성 패키지 설치 (레이어 캐싱 활용)
# 소스 코드가 변경되더라도 requirements.txt가 변하지 않으면 이 단계는 캐시를 재사용합니다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 7. 프로젝트 소스코드 전체 복사 및 권한 부여
# .dockerignore에 명시된 파일/폴더는 제외됩니다.
COPY . .
RUN chown -R qa_user:qa_user /app

# 8. 파이썬 모듈 인식 경로 설정
ENV PYTHONPATH=/app

# 9. Non-root 유저로 전환
USER qa_user

# 10. 컨테이너 실행 시 기본 명령어 (docker-compose에서 오버라이딩 가능)
CMD ["pytest", "tests/", "-n", "auto", "--alluredir=reports/allure-results"]