pipeline {
    agent {
        kubernetes {
            inheritFrom 'python3.9'
        }
    }

    environment {
        REPOSITORY_URI = 'docker-bk.agileforge.tech/devops'
        REPOSITORY_PROTOCOL = 'https'
        NEXUS_CRED = credentials('nexus-registry')
        GROUP_ID = 'tech.bitkernel.devops'
        git_url = 'https://github.com/dumasd/config-ops.git'
        gitCredential = 'thinkerwolf'
        kubeCredential = 'bik-devops-kubeconfig'
    }

    stages {
        stage('Env') {
            steps {
                script {
                    def version = new Date().format('yyyyMMddHHmmss') + "-${env.BUILD_ID}"
                    env.RELEASE_VERSION = version
                }
            }
        }

        stage('SCM Checkout') {
            steps {
                container('git') {
                    git branch: 'main', credentialsId: gitCredential, url: "${git_url}"
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

                    nexusArtifactPublish(
                        serverId: 'nexus',
                        repository: 'raw-public',
                        groupId: "${GROUP_ID}",
                        artifactId: 'config-ops',
                        version: "${RELEASE_VERSION}",
                        includes: "config-ops-linux-${RELEASE_VERSION}.tar.gz")
                }
                container('buildah') {
                    script {
                        def imageName = "${REPOSITORY_URI}/config-ops:${RELEASE_VERSION}"
                        env.IMAGE = imageName
                        sh '''
                            buildah login -u $NEXUS_CRED_USR -p $NEXUS_CRED_PSW $REPOSITORY_PROTOCOL://$REPOSITORY_URI
                            buildah build  --storage-driver vfs -t $IMAGE -f Dockerfile .
                            buildah push --storage-driver vfs $IMAGE
                        '''
                        def deployFilePath = 'deploy.yaml'
                        // 替换k8s文件镜像
                        contentReplace(configs:[
                            fileContentReplaceConfig(configs: [
                                fileContentReplaceItemConfig(replace: imageName, search: '\\$IMAGE')
                            ], fileEncoding: 'UTF-8', filePath: deployFilePath, lineSeparator: 'Unix')
                        ])
                        // 存放文件，用于不同agent共享
                        stash name: 'deployFile', includes: deployFilePath
                    }
                }
            }
        }

        stage('Deploy') {
            agent {
                kubernetes {
                    inheritFrom 'kubectl'
                }
            }
            steps {
                withKubeConfig(credentialsId: kubeCredential, serverUrl: '') {
                    container('kubectl') {
                        unstash 'deployFile'
                        sh '''
                        kubectl apply -f deploy.yaml
                        '''
                    }
                }
            }
        }
    }
}
