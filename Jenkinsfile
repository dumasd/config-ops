/* groovylint-disable LineLength, NestedBlockDepth, DuplicateStringLiteral */
pipeline {
    agent {
        kubernetes {
            yaml '''
            apiVersion: v1
            kind: Pod
            spec:
              containers:
              - name: python
                image: wukaireign/python:3.9-ubuntu-18
                imagePullPolicy: Always
                command:
                  - cat
                tty: true
              - name: git
                image: bitnami/git:latest
                command:
                  - cat
                tty: true
              - name: buildah
                image: quay.io/buildah/stable:latest
                command:
                  - cat
                tty: true
              - name: gh
                image: ghcr.io/github/cli/gh:latest
                command:
                  - cat
                tty: true
            '''
        }
    }

    parameters {
        gitParameter(name: 'TAG',
            type: 'PT_TAG',
            defaultValue: 'v0.0.1',
            tagFilter: '*',
            quickFilterEnabled: true,
            requiredParameter: true,
            selectedValue: 'NONE',
            sortMode: 'NONE',
        )
    }

    environment {
        REPOSITORY_URI = 'docker.io/wukaireign'
        REPOSITORY_PROTOCOL = 'https'
        // DOCKER_CRED = credentials('nexus-cred')
        DOCKER_CRED = credentials('devops-docker-cred')
        GROUP_ID = 'tech.bitkernel.devops'
        GITHUB_TOKEN = credentials('GITHUB_TOKEN')
        git_url = 'https://github.com/dumasd/config-ops.git'
        gitCredential = 'thinkerwolf'
        kubeCredential = 'bik-devops-kubeconfig'
    }

    stages {
        stage('SCM Checkout') {
            steps {
                container('git') {
                    checkout scmGit(
                        branches: [[name: "refs/tags/${TAG}"]],
                        extensions: [cloneOption(shallow: true)],
                        userRemoteConfigs: [[credentialsId: gitCredential, url: "${git_url}"]]
                    )
                }
            }
        }

        stage('Build') {
            steps {
                container('python') {
                    echo "Build tag: ${TAG}"
                    sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip3 install -r requirements.txt
                    pip3 install pyinstaller
                    pyinstaller app.spec

                    mkdir -p dist/app/jdbc-drivers
                    cp config.yaml.sample dist/app
                    cp startup.sh dist/app
                    cp jdbc-drivers/* dist/app/jdbc-drivers
                    cp README.md dist/app

                    tar -czf config-ops-linux.tar.gz -C dist/app .
                    '''
                }

                container('gh') {
                    sh """
                    echo ${GITHUB_TOKEN} > .github_token
                    gh auth login --with-token < .github_token
                    gh release create ${TAG} *.tar.gz \
                          --repo  dumasd/config-ops \
                          --target main
                    """
                }

                container('buildah') {
                    script {
                        def imageName = "${REPOSITORY_URI}/config-ops:${TAG}"
                        env.IMAGE = imageName
                        sh '''
                            buildah login -u $DOCKER_CRED_USR -p $DOCKER_CRED_PSW $REPOSITORY_PROTOCOL://$REPOSITORY_URI
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
