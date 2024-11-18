from setuptools import setup, find_packages

setup(
    name="configops",  # PyPI 上的包名
    version="0.2.2",  # 初始版本
    description="A devops config tool",
    author="Bruce Wu",
    author_email="wukai213@gmail.com",
    url="https://github.com/dumasd/config-ops",
    packages=find_packages(),  # 自动发现项目中的所有包
    include_package_data=True,  # 包括静态文件
    install_requires=[
        "blinker==1.8.2",
        "click==8.1.7",
        "Flask==3.0.3",
        "itsdangerous==2.2.0",
        "Jinja2==3.1.4",
        "MarkupSafe==2.1.5",
        "nacos-sdk-python==1.0.0",
        "Werkzeug==3.0.3",
        "configobj==5.0.8",
        "jproperties==2.1.2",
        "ruamel.yaml==0.18.6",
        "ruamel.yaml.clib==0.2.8",
        "marshmallow==3.21.3",
        "Flask-SQLAlchemy==3.1.1",
        "sqlalchemy==2.0.32",
        "typing-extensions==4.12.2",
        "protobuf==3.20.1",
        "mysql-connector-python==8.0.30",
        "sqlfluff>=3.1.1",
        "psycopg2-binary==2.9.9",
        "jsonschema==4.23.0",
    ],
    entry_points={
        "console_scripts": [
            "configops=configops.cli.main:cli",  # CLI 命令及其入口
        ],
    },
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
