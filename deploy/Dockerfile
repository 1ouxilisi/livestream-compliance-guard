# livestream-compliance-guard —— 远程 MCP 运行镜像（Railway / Render / Fly / 腾讯云轻量通用）
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PIP_NO_CACHE_DIR=1 \
    LCG_HTTP_HOST=0.0.0.0 \
    LCG_HTTP_PORT=8000

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# 安装本包 + HTTP 传输 + LLM 语义层（对应 pyproject 的 [http]/[llm] extra；模型 key 由环境变量注入）
RUN pip install --no-cache-dir ".[http,llm]"

# 构建期即跑规则自检，任何规则/引擎回归都会让镜像构建失败
RUN python server.py --selftest >/dev/null

EXPOSE 8000

# 免鉴权探活 /healthz；公网务必用环境变量 LCG_BEARER_TOKEN 注入令牌（平台 Secret，不写进镜像）
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=5).status==200 else 1)"

# 常驻远程 MCP：MCP 端点 /mcp，探活 /healthz
#   docker build -f deploy/Dockerfile -t lcg .
#   docker run --rm -p 8000:8000 -e LCG_BEARER_TOKEN=sk-xxx lcg
CMD ["python", "-m", "lcg.server_http"]
