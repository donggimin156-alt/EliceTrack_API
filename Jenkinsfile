// team2-api — Multibranch Pipeline (develop / main)
// 실행 스크립트 SSOT: scripts/run_lint.sh, scripts/run_tests.sh, scripts/publish_allure_latest.sh
//
// Allure Jenkins 연동 (팀원 가이드):
//   1) Plugins: Allure 설치
//   2) (권장) Manage Jenkins → Tools → Allure Commandline Name=allure, Install automatically
//      → VM에 allure CLI가 이미 있으면 생략 가능
//   3) post { allure results: reports/allure-results }
//
// - Push: smoke → 없으면 tests/api/ (-m api)
// - develop 0시(KST): tests/ full (서버 TZ=Asia/Seoul)
// - 테스트/린트 실패: UNSTABLE (GitLab 머지와 무관)

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
                    pip install -r requirements-dev.txt
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

        stage('Test') {
            steps {
                script {
                    def branch = env.BRANCH_NAME ?: 'develop'
                    def isNightly = currentBuild.getBuildCauses(
                        'hudson.triggers.TimerTrigger$TimerTriggerCause'
                    ).size() > 0

                    if (isNightly && branch == 'develop') {
                        env.PYTEST_MARKER = ''
                        echo 'Nightly full regression (develop)'
                    } else if (branch == 'develop' || branch == 'main') {
                        def smokeLine = sh(
                            script: '''
                                . .venv/bin/activate
                                pytest tests/ --collect-only -q -m smoke 2>&1 | tail -n 1
                            ''',
                            returnStdout: true
                        ).trim()
                        env.PYTEST_MARKER = smokeLine.contains('no tests collected') ? 'api' : 'smoke'
                    } else {
                        error("Unexpected branch: ${branch}")
                    }
                }
                catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE') {
                    sh '''
                        . .venv/bin/activate
                        export TARGET="${TARGET}"
                        ./scripts/run_tests.sh "${PYTEST_ENV}" "${PYTEST_MARKER}"
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
