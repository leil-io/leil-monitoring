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
          # Skip integration tests that require a live SaunaFS master
          pytest -m "not integration" -q --junitxml=reports/junit.xml
        '''
      }
      post {
        always {
          junit allowEmptyResults: true, testResults: 'reports/junit.xml'
        }
      }
    }

    stage('Integration tests (192.168.50.189)') {
      steps {
        sh '''
          . "$VENV/bin/activate"
          mkdir -p reports
          # Skip integration tests that require a live SaunaFS master
          pytest -m "integration" -q --junitxml=reports/junit.xml
        '''
      }
      post {
        always {
          junit allowEmptyResults: true, testResults: 'reports/junit.xml'
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
          docker.withRegistry('https://registry.saunafs.com', 'harbor') {
            sh """
              docker tag saunafs-monitoring:latest registry.saunafs.com/library/saunafs-monitoring:${GIT_COMMIT}
              docker tag saunafs-monitoring:latest registry.saunafs.com/library/saunafs-monitoring:${GIT_COMMIT}
              docker tag saunafs-api:latest registry.saunafs.com/library/saunafs-api:${GIT_COMMIT}
              docker tag saunafs-api:latest registry.saunafs.com/library/saunafs-api:${GIT_COMMIT}
              """
            docker.image("registry.saunafs.com/library/saunafs-monitoring:latest").push()
            docker.image("registry.saunafs.com/library/saunafs-monitoring:${GIT_COMMIT}").push()
            docker.image("registry.saunafs.com/library/saunafs-api:latest").push()
            docker.image("registry.saunafs.com/library/saunafs-api:${GIT_COMMIT}").push()
          }
        }
      }
      post {
        always {
          sh '''
            docker logout registry.saunafs.com
            '''
        }
      }
    }
  }
}
