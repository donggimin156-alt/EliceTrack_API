// team2-api — Multibranch Pipeline (develop / main)
// 실행 스크립트 SSOT: scripts/run_lint.sh, scripts/run_tests.sh, scripts/publish_allure_latest.sh
//
// Allure Jenkins 연동 (팀원 가이드):
//   1) Plugins: Allure 설치
//   2) (권장) Manage Jenkins → Tools → Allure Commandline Name=allure, Install automatically
//      → VM에 allure CLI가 이미 있으면 생략 가능
//   3) post { allure results: reports/allure-results }
//
// [풀 테스트 트리거]
// - GitLab develop/main push(머지) → Multibranch가 빌드 → 아래 stage('Test') 실행
// - develop 매일 0시 → trigger 발동 → 같은 stage('Test') 실행
// 실제 pytest 범위는 stage('Test')에서 run_tests.sh 2번째 인자(marker)를 생략할 때 tests/ 전체 (scripts/run_tests.sh 참고)

pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }

    environment {
        CREDENTIALS_ENV_FILE = 'team2-api-env-file'
        ALLURE_PUBLIC_ROOT = '/var/www/allure'
        PYTHON = 'python3'
    }

    triggers {
        // develop만: 매일 0시(KST) 풀 회귀 1회
        cron(env.BRANCH_NAME == 'develop' ? '0 0 * * *' : '')
    }

    stages {
        stage('Prepare') {
            steps {
                script {
                    def branch = env.BRANCH_NAME ?: 'develop'
                    env.TARGET = (branch == 'main') ? 'prod' : 'dev'
                    env.PYTEST_ENV = 'qa'
                    env.GIT_BRANCH = branch
                    // GitLab 전용 CI 변수를 코드(jira/discord/slack)가 읽으므로 Jenkins 값으로 매핑한다.
                    // 이게 없으면 Jira 티켓 job_url이 "로컬 실행 환경", 알림 branch가 "local"로 찍힌다.
                    env.CI_COMMIT_BRANCH = env.BRANCH_NAME
                    env.CI_JOB_URL = env.BUILD_URL
                    env.CI_PIPELINE_SOURCE = 'jenkins'
                }
                withCredentials([
                    file(credentialsId: "${env.CREDENTIALS_ENV_FILE}", variable: 'ENV_FILE'),
                ]) {
                    sh '''
                        cp "$ENV_FILE" .env
                        chmod 600 .env
                        chmod +x scripts/*.sh
                    '''
                }
                sh '''
                    ${PYTHON} -m venv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    mkdir -p reports
                '''
            }
        }

        stage('Lint') {
            steps {
                catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE') {
                    sh '''
                        . .venv/bin/activate
                        ./scripts/run_lint.sh ci
                    '''
                }
            }
        }

        // ===== 풀 회귀 테스트 (tests/ 전체, -m smoke/api 없음) =====
        // 머지 push / develop 0시 테스트 모두 이 stage만 사용 
        stage('Test') {
            steps {
                script {
                    def branch = env.BRANCH_NAME ?: 'develop'
                    if (branch != 'develop' && branch != 'main') {
                        error("Unexpected branch: ${branch}")
                    }
                    def isScheduled = currentBuild.getBuildCauses(
                        'hudson.triggers.TimerTrigger$TimerTriggerCause'
                    ).size() > 0
                    if (isScheduled && branch == 'develop') {
                        echo 'Scheduled full regression (develop, 0:00)'
                    } else {
                        echo "Push/merge full regression (${branch})"
                    }
                }
                catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE') {
                    // marker 인자 없음 → run_tests.sh: pytest tests/  (풀 테스트)
                    sh '''
                        . .venv/bin/activate
                        export TARGET="${TARGET}"
                        # .env는 로컬 안전을 위해 false. CI 풀 회귀에서만 Jira 자동 버그 생성을 켠다.
                        # load_dotenv는 기존 env를 override하지 않으므로 이 export가 .env의 false보다 우선한다.
                        export ENABLE_JIRA_AUTO_BUG=true
                        ./scripts/run_tests.sh "${PYTEST_ENV}"
                    '''
                }
            }
        }

        stage('Allure (latest URL)') {
            steps {
                sh '''
                    export BRANCH="${BRANCH_NAME}"
                    export ALLURE_PUBLIC_ROOT="${ALLURE_PUBLIC_ROOT}"
                    if command -v allure >/dev/null 2>&1; then
                      ./scripts/publish_allure_latest.sh
                    else
                      echo "Skip publish_allure_latest — no allure CLI"
                    fi
                '''
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'reports/junit.xml,reports/test_execution.log', allowEmptyArchive: true
            allure includeProperties: false, jdk: '', results: [[path: 'reports/allure-results']]
        }
        success {
            echo "Allure (latest): http://61.107.201.242/allure/${env.BRANCH_NAME}/latest/"
        }
        unstable {
            echo 'Lint/Test UNSTABLE — GitLab merge is not blocked by this job.'
        }
    }
}

