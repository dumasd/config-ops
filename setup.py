from setuptools import setup, find_packages

setup(
    name="configops",  # PyPI 上的包名
    version="0.1.4",  # 初始版本
    description="A devops config tool",
    author="Bruce Wu",
    author_email="wukai213@gmail.com",
    url="https://github.com/dumasd/config-ops",    
    packages=find_packages(),  # 自动发现项目中的所有包
    include_package_data=True,  # 包括静态文件
    install_requires=[
        "click",
    ],
    entry_points={
        "console_scripts": [
            "configops=ops.cli.main:cli",  # CLI 命令及其入口
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
