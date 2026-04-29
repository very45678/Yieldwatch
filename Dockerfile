FROM python:3.10-slim

WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
# 分阶段安装，先安装核心依赖，再安装 akshare（更大更慢）
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir fastapi uvicorn httpx apscheduler pydantic pydantic-settings jinja2 chinesecalendar redis && \
    pip install --no-cache-dir akshare

# 复制应用代码
COPY app/ ./app/

EXPOSE 10000

# 启动命令，增加超时设置
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000", "--timeout-keep-alive", "5"]
