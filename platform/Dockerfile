# 使用官方Python运行时作为父镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制requirements文件
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制当前目录内容到工作目录
COPY . .

# 暴露端口
EXPOSE 8000

# 运行应用
CMD ["python", "main.py"]