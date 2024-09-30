# config-ops

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)[![Build Status](https://github.com/apache/superset/workflows/Python/badge.svg)](https://github.com/apache/superset/actions)

一款 DevOps 配置工具：

- Nacos Yaml、Properties格式的配置文件变更。
- 使用 Liquibase 执行数据库版本脚本。

结合 [dumasd/jenkins-config-ops-plugin (github.com)](https://github.com/dumasd/jenkins-config-ops-plugin) 插件实现与Jenkins的集成。

## 快速开始

### 部署Liquibase

Liquibase安装文档: https://docs.liquibase.com/start/install/home.html

### 部署Config-Ops

#### 本地部署

下载 [Config-Ops Release](https://github.com/dumasd/config-ops/releases/latest/download/config-ops-linux.tar.gz)  文件解压，release 文件中包含 `config-ops` 可执行文件和配置文件样例 `config.yaml.sample`

```shell
# 从sample中拷贝出一个配置文件，修改配置文件中的配置
cp config.yaml.sample config.yaml

# 修改配置
vim config.yaml

# 启动服务
./startup.sh

```

#### Docker部署

config-ops镜像库： [wukaireign/config-ops general | Docker Hub](https://hub.docker.com/repository/docker/wukaireign/config-ops/general)

```shell
git clone https://github.com/dumasd/config-ops.git

cd config-ops

# 修改 docker-compose.yaml CONFIGOPS_CONFIG 部分
vim docker-compose.yaml

# docker-compose启动应用
docker-compose -f docker-compose.yaml up -d
```

## 本地开发

### 要求

- Python：3.9及以上版本

### 开发环境设置

```shell
# 拉取代码 
git clone https://github.com/dumasd/config-ops.git
cd config-ops

# 设置python虚拟环境
python3 -m venv .venv
. .venv/bin/activate

# 安装依赖
pip3 install -r requirements.txt

# Run Tests
python3 -m pytest ./tests

# pyinstaller 打包成可执行的二进制
pyinstaller app.spec 

# 发布到pipy
pip3 install --upgrade setuptools wheel twine
python3 setup.py sdist bdist_wheel
python3 -m twine upload dist/*


```
