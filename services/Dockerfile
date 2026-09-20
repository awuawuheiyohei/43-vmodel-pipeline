FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# 复制代码
COPY app/ ./app/
COPY prompts/ ./prompts/

EXPOSE 8000

# 启动 FastAPI（uvicorn）
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]