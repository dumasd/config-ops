pipeline { 
    agent {
        kubernetes {
            inheritFrom 'python3.9'
        }
    }

    parameters {
        string defaultValue: '1.0.0', name: 'RELEASE_VERSION'
    }

    environment {
        git_url = 'https://github.com/dumasd/config-ops.git'
        gitCredential = 'thinkerwolf'
    }

    stages {
        stage('SCM Checkout') {
            steps {
                container('git') {
                    git branch: "main", credentialsId: gitCredential, url: "${git_url}"
                }
            }
        }

        stage('Build') {
            steps {
                container('python') {
                    sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip3 install -r requirements.txt
                    pip3 install pyinstaller
                    pyinstaller app.spec

                    cp config.yaml.sample dist/app
                    cp README.md dist/app
                    tar -czf config-ops-linux-${RELEASE_VERSION}.tar.gz --exclude _internal -C dist/app .
                    '''
                }
            }
        }
    }
}