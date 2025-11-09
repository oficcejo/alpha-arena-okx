# 使用Python 3.11官方镜像作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 复制项目文件
COPY run.py .
COPY deepseekok2.py .
COPY data_manager.py .
COPY streamlit_app.py .
COPY .streamlit/ .streamlit/

# 创建数据目录
RUN mkdir -p /app/data

# 暴露Streamlit端口
EXPOSE 8501

# 健康检查 - 检查Web界面和run.py进程
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health && pgrep -f "python.*run.py" || exit 1

# 统一启动入口
CMD ["python", "-u", "run.py"]

