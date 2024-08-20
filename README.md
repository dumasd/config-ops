# config-ops

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)[![Build Status](https://github.com/apache/superset/workflows/Python/badge.svg)](https://github.com/apache/superset/actions)

一款Nacos配置增量变更和数据库脚本执行的工具，目前支持：

- Nacos Yaml、Properties格式的配置文件变更。
- MySQL 脚本执行。

## 快速开始 {shell}

下载 release 文件解压，release 文件中包含 `config-ops` 可执行文件和配置文件样例 `config.yaml.sample`

```shell
# 从sample中拷贝出一个配置文件，修改配置文件中的配置
cp config.yaml.sample config.yaml

# 查看参数选项
./config-ops --help

# 启动程序
./config-ops --host 127.0.0.1 --port 5000 --config config.yaml
```

## 本地开发

### 要求

- Python3.8及以上版本

### 开发环境设置

```shell
# 拉取代码 
https://github.com/dumasd/config-ops.git
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
