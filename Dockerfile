FROM python:3.10-slim

WORKDIR /app

# 使用国内镜像加速
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 10000

# 支持环境变量 PORT，Zeabur 会自动设置
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}
