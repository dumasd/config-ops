import os
import platform

def get_jar_classpath(directory):
    print(os.path.abspath(directory))
    base = os.path.abspath(directory)
    # 获取操作系统类型
    separator = ';' if platform.system() == 'Windows' else ':'
    
    # 遍历目录下的 JAR 文件
    jar_files = [f for f in os.listdir(base) if f.endswith('.jar')]
    
    for jar in jar_files:
        print(jar)

    
    # 构造 classpath 字符串
    classpath = separator.join(os.path.join(base, jar) for jar in jar_files)
    
    return classpath

# 示例用法
directory_path = 'jdbc-drivers'  # 替换为你的 JAR 文件所在目录
classpath = get_jar_classpath(directory_path)
print(f"Classpath: {classpath}")

print(os.getcwd())