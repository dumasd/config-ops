# config-ops

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)[![Build Status](https://github.com/apache/superset/workflows/Python/badge.svg)](https://github.com/apache/superset/actions)

一款 DevOps 配置工具，目前支持：

- Nacos Yaml、Properties格式的配置文件变更。
- MySQL 脚本执行（后续进行扩展，执行多种类型数据库）。
- Redis 脚本执行（待规划）。

结合 [dumasd/jenkins-config-ops-plugin (github.com)](https://github.com/dumasd/jenkins-config-ops-plugin) 插件实现与Jenkins的集成。

## 快速开始

### Docker

config-ops镜像库： [wukaireign/config-ops general | Docker Hub](https://hub.docker.com/repository/docker/wukaireign/config-ops/general)

```shell
git clone https://github.com/dumasd/config-ops.git

cd config-ops

# 修改 docker-compose.yaml CONFIGOPS_CONFIG 部分
vim docker-compose.yaml

# docker-compose启动应用
docker-compose -f docker-compose.yaml up -d
```

### 本地启动

下载 release 文件解压，release 文件中包含 `config-ops` 可执行文件和配置文件样例 `config.yaml.sample`

```shell
# 从sample中拷贝出一个配置文件，修改配置文件中的配置
cp config.yaml.sample config.yaml

# 修改配置
vim config.yaml

# 设置配置文件变量
export CONFIGOPS_CONFIG_FILE=config.yaml
# 设置HOST（可选)
# export CONFIGOPS_HOST="127.0.0.1"
# 设置端口（可选)
# export CONFIGOPS_PORT=5000

# 启动服务
./startup.sh

```

## 本地开发

### 要求

- Python：3.8及以上版本

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
```
