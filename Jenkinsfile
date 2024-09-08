/* groovylint-disable LineLength, NestedBlockDepth, DuplicateStringLiteral */
pipeline {
    agent {
        kubernetes {
            inheritFrom 'python3.9'
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
                    createGitHubRelease(
                        credentialId: gitCredential,
                        repository: "dumasd/config-ops",
                        commitish: "main",
                        tag: "${TAG}",
                        draft: true
                    )

                    uploadGithubReleaseAsset(
                        credentialId: gitCredential,
                        repository: "dumasd/config-ops",
                        tagName: "${TAG}",
                        uploadAssets: [
                            [filePath: 'config-ops-linux.tar.gz'],
                        ]
                    )
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
