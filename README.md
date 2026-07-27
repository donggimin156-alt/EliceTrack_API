# 엘리스 LMS API QA 자동화 프로젝트

엘리스 LMS(학습 관리 플랫폼)의 백엔드 API를 대상으로 테스트 자동화를 진행한 프로젝트입니다.

기간: 2026.07.09 ~ 2026.07.27

팀: 4인

* * *

브랜치 구성

requests — Python + Requests + Pytest 기반 팀 프로젝트

* * *

requests 브랜치

사용 도구

Python, Pytest, Requests, Pydantic, JSON Schema, Jenkins(Multibranch Pipeline), Allure Report, Slack / Discord Webhook, Jira, JMeter, Ruff

팀 전체에서 Jenkins Multibranch 파이프라인을 구성해 Lint → 테스트 실행 → Allure 리포트 자동 발행 → Slack/Discord 알림 → Jira 이슈 자동 등록까지 이어지는 흐름을 만들었습니다. 원 저장소(GitLab)에서는 브랜치에 따라 대상 환경이 자동으로 갈리고(main은 prod, develop은 dev), develop은 매일 0시에 전체 회귀가 한 번 더 돌아갑니다.

테스트는 UI를 거치지 않고 API를 직접 호출해 검증합니다. 응답은 도메인별 JSON Schema로 구조를 먼저 검증한 뒤 값을 확인하며, 학습자(learner)와 교육자(educator) 두 권한을 각각 픽스처로 분리해 권한별 시나리오를 나눠 검증합니다.

* * *

디렉터리 구조

    api/
      base_client.py      공통 HTTP 클라이언트 (세션, 재시도, 로깅)
      endpoints/          도메인별 API 클라이언트
      schemas/            응답 검증용 JSON Schema
    core/config.py        Pydantic 기반 환경 설정 SSOT (dev/prod 분기)
    fixtures/             인증 토큰, 테스트 데이터 셋업/티어다운
    hooks/                Pytest 훅 (Allure, Slack, Discord, Jira 연동)
    tests/api/            board, class, class_lecture, classhome, schedule
    utils/                assertions 헬퍼, jira, slack, discord 클라이언트
    scripts/              run_tests.sh, run_lint.sh, publish_allure_latest.sh
    performance_test/     JMeter 부하 테스트 시나리오
    Jenkinsfile           CI 파이프라인 정의

* * *

내가 한 것:

프레임워크 초기 구조를 설계하고, 게시판(Board) 도메인 테스트와 알림·이슈 자동화 연동을 담당했습니다.

게시판 API 클라이언트를 만들어 흩어져 있던 요청 로직 22개 메서드를 `BoardApiClient` 한 곳으로 모았습니다. 이후 반복되던 성공/실패 판정 assert를 `board_ok` / `board_fail` 헬퍼로 통일하고 JSON Schema 검증을 도입해, 응답 구조가 바뀌었을 때 테스트마다 고치는 대신 스키마 파일 하나만 수정하면 되도록 바꿨습니다. 글 생성 셋업은 `make_article` 팩토리 픽스처로 추출해 중복 셋업 코드를 제거했습니다. 한 파일에 쌓여 있던 게시판 테스트 68개는 기능별(작성·댓글·좋아요·첨부·권한·보안 등) 7개 파일로 분리했습니다.

Jira 연동은 테스트 실패를 사람이 옮겨 적지 않아도 되게 만드는 데 초점을 뒀습니다. `@pytest.mark.jira("EQA-5")` 마커로 테스트와 이슈를 연결해 실패 시 해당 이슈에 자동으로 코멘트가 달리고, 마커가 없는 신규 실패는 티켓을 새로 생성합니다. 같은 요약의 미해결 이슈가 이미 있으면 재사용해 중복 티켓이 쌓이지 않게 했고, 티켓 본문에 실패한 HTTP 요청/응답과 payload를 함께 넣어 재현 없이도 원인을 볼 수 있게 했습니다. 고쳐진 버그는 XPASS 감지로 알려줍니다.

알림 쪽에서는 요약 집계가 Allure의 Total과 맞지 않던 문제를 잡았습니다. xfail과 error가 누락돼 숫자가 어긋나던 것을 보정하고, Skipped와 xfail을 분리 표시해 "알려진 버그로 실패 중인 것"과 "아예 안 돈 것"을 구분할 수 있게 했습니다.

CI는 팀이 GitLab CI에서 Jenkins로 옮기는 과정에서, 코드가 읽던 GitLab 전용 환경 변수를 Jenkins 값으로 매핑했습니다. 이 매핑이 없으면 Jira 티켓의 job_url이 "로컬 실행 환경"으로, 알림의 브랜치가 "local"로 찍혀 어느 빌드에서 난 실패인지 추적할 수 없었습니다.

팀 전체 테스트 케이스 235개 (board 68, class 126, schedule 18, classhome 16, class_lecture 7)

* * *

실행 방법

    python -m venv .venv
    source .venv/Scripts/activate
    pip install -r requirements.txt
    pip install -r requirements-dev.txt

`.env.example`을 `.env`로 복사해 값을 채웁니다. `.env`는 gitignore 대상이며 CI에서는 Jenkins Credentials로 주입됩니다.

    # 전체 실행 (TARGET으로 dev/prod 선택)
    TARGET=dev pytest tests/ --alluredir=reports/allure-results

    # 도메인/우선순위 마커로 좁혀 실행
    pytest -m board
    pytest -m "api and p0"
    pytest -m "schedule and educator"

    # CI와 동일한 방식으로 실행 (Allure 리포트까지 생성)
    ./scripts/run_tests.sh qa

    # 리포트 열기
    allure serve reports/allure-results

* * *

코드 품질

Ruff로 린트와 포맷을 강제하며, CI의 Lint 스테이지에서 동일한 스크립트가 실행됩니다.

    ./scripts/run_lint.sh
