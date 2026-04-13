// This file is part of saunafs-monitoring.
// Copyright (C) 2025 Leil Storage OÜ
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License version 3 as
// published by the Free Software Foundation.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>.
pipeline {
  agent {
    label "ansible"
  }

  options {
    timestamps()
    ansiColor('xterm')
  }

  environment {
    PIP_DISABLE_PIP_VERSION_CHECK = '1'
    PYTHONDONTWRITEBYTECODE = '1'
    VENV = '.venv'
    SAUNAFS_MASTER_HOST = '127.0.0.1'
    SAUNAFS_MASTER_PORT = '9421'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
        sh 'python3 --version || true'
      }
    }

    stage('Setup Python') {
      steps {
        sh '''
          python3 -m venv "$VENV"
          . "$VENV/bin/activate"
          python -m pip install --upgrade pip
          # Project deps + test tooling
          pip install -r requirements.txt pytest
        '''
      }
    }

    stage('Unit tests') {
      steps {
        sh '''
          . "$VENV/bin/activate"
          mkdir -p reports
          # Skip integration tests that require a live LeilFS master
          pytest tests -m "not integration" -q --junitxml=reports/junit.xml
        '''
      }
      post {
        always {
          junit allowEmptyResults: true, testResults: 'reports/junit.xml'
        }
      }
    }

    stage('Integration tests (Compose cluster)') {
      steps {
        script {
          env.SAUNAFS_VERSION = sh(
            script: '''
              . "$VENV/bin/activate"
              python utils/get_latest_saunafs_version.py
            ''',
            returnStdout: true,
          ).trim()

          if (!env.SAUNAFS_VERSION) {
            error('Failed to resolve SaunaFS version from debian-package tags')
          }
        }
        sh '''
          . "$VENV/bin/activate"
          mkdir -p reports

          echo "Using SaunaFS version: $SAUNAFS_VERSION"

          if docker compose version >/dev/null 2>&1; then
            COMPOSE="docker compose"
          else
            COMPOSE="docker-compose"
          fi

          $COMPOSE -f docker-compose.ci.yaml pull
          $COMPOSE -f docker-compose.ci.yaml up -d master metalogger cgi chunkserver01

          ready=0
          for _ in $(seq 1 30); do
            if bash -c '</dev/tcp/127.0.0.1/9421' >/dev/null 2>&1; then
              ready=1
              break
            fi
            sleep 2
          done

          if [ "$ready" -ne 1 ]; then
            $COMPOSE -f docker-compose.ci.yaml logs || true
            echo "SaunaFS master did not become reachable on 127.0.0.1:9421"
            exit 1
          fi

          $COMPOSE -f docker-compose.ci.yaml up -d client

          # Copy and run the hello writer shell script inside the client container
          wrote=0
          for _ in $(seq 1 30); do
            if docker inspect -f '{{.State.Running}}' saunafs-client 2>/dev/null | grep -q true; then
              docker cp utils/write_hello.sh saunafs-client:/tmp/write_hello.sh >/dev/null 2>&1 || true
              if docker exec saunafs-client sh /tmp/write_hello.sh >/dev/null 2>&1; then
                wrote=1
                break
              fi
            fi
            sleep 2
          done

          if [ "$wrote" -ne 1 ]; then
            $COMPOSE -f docker-compose.ci.yaml logs || true
            echo "Failed to write to /mnt/saunafs from saunafs-client"
            exit 1
          fi

          pytest tests -m "integration" -q --junitxml=reports/junit.xml
        '''
      }
      post {
        always {
          junit allowEmptyResults: true, testResults: 'reports/junit.xml'
          sh '''
            if docker compose version >/dev/null 2>&1; then
              COMPOSE="docker compose"
            else
              COMPOSE="docker-compose"
            fi

            $COMPOSE -f docker-compose.ci.yaml logs || true
            $COMPOSE -f docker-compose.ci.yaml down -v || true
            sudo rm -rf ./volumes || true
          '''
        }
      }
    }

    stage('Build Docker Images') {
      steps {
        sh '''
          # Build UI/monitoring service image
          docker build -t saunafs-monitoring:latest -f Dockerfile .
          # Build API service image
          docker build -t saunafs-api:latest -f Dockerfile.api .
        '''
      }
    }
    stage('Push Docker Images') {
      when {
        branch "dev"
      }
      steps {
        script {
          sh """
            docker tag saunafs-monitoring:latest registry.leil.io/library/saunafs-monitoring:${GIT_COMMIT}
            docker tag saunafs-monitoring:latest registry.leil.io/library/saunafs-monitoring:latest
            docker tag saunafs-api:latest registry.leil.io/library/saunafs-api:${GIT_COMMIT}
            docker tag saunafs-api:latest registry.leil.io/library/saunafs-api:latest
            """
          docker.withRegistry('https://registry.leil.io', 'harbor') {
            docker.image("registry.leil.io/library/saunafs-monitoring:${GIT_COMMIT}").push()
            docker.image("registry.leil.io/library/saunafs-monitoring:latest").push()
            docker.image("registry.leil.io/library/saunafs-api:${GIT_COMMIT}").push()
            docker.image("registry.leil.io/library/saunafs-api:latest").push()
          }
        }
      }
      post {
        always {
          sh '''
            docker logout registry.leil.io
            '''
        }
      }
    }
  }
}
