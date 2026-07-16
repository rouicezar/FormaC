#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_DIR="$PROJECT_DIR/.runtime"
ENV_FILE="$PROJECT_DIR/.env"
COMPOSE_FILE="$PROJECT_DIR/deploy/docker-compose.yml"

mkdir -p "$RUNTIME_DIR"
if [[ ! -f "$ENV_FILE" ]]; then
  cp "$PROJECT_DIR/deploy/.env.example" "$ENV_FILE"
  echo "已从示例创建 $ENV_FILE"
fi

set -a
source "$ENV_FILE"
set +a
export NO_PROXY="${NO_PROXY:-localhost,127.0.0.1}"
export no_proxy="${no_proxy:-localhost,127.0.0.1}"

for command in docker uv npm ollama curl; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "缺少运行命令：$command" >&2
    exit 1
  fi
done

if pgrep -f "$PROJECT_DIR/backend/.venv/bin/uvicorn app.main:app" >/dev/null && \
   { [[ ! -f "$RUNTIME_DIR/backend.pid" ]] || ! kill -0 "$(cat "$RUNTIME_DIR/backend.pid")" 2>/dev/null; }; then
  echo "检测到残留后端进程，请先运行 scripts/stop.sh 清理。" >&2
  exit 1
fi

if pgrep -f "$PROJECT_DIR/frontend/node_modules/.bin/vite" >/dev/null && \
   { [[ ! -f "$RUNTIME_DIR/frontend.pid" ]] || ! kill -0 "$(cat "$RUNTIME_DIR/frontend.pid")" 2>/dev/null; }; then
  echo "检测到残留前端进程，请先运行 scripts/stop.sh 清理。" >&2
  exit 1
fi

if [[ -f "$RUNTIME_DIR/backend.pid" ]] && kill -0 "$(cat "$RUNTIME_DIR/backend.pid")" 2>/dev/null; then
  echo "后端已经运行。"
else
  docker compose -f "$COMPOSE_FILE" up -d
  echo "正在等待 PostgreSQL 就绪……"
  for _ in {1..45}; do
    if docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U pkcs -d private_knowledge >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  if ! docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U pkcs -d private_knowledge >/dev/null 2>&1; then
    echo "PostgreSQL 未能就绪，请运行 scripts/status.sh 查看状态。" >&2
    exit 1
  fi

  for model in embeddinggemma:latest "${PKCS_OLLAMA_MODEL:-qwen3:0.6b}"; do
    if ! ollama list | awk 'NR > 1 {print $1}' | grep -Fx "$model" >/dev/null; then
      echo "首次运行需要安装 Ollama 模型：$model"
      ollama pull "$model"
    fi
  done

  (
    cd "$PROJECT_DIR/backend"
    uv sync
    uv run alembic upgrade head
    nohup uv run uvicorn app.main:app --host 127.0.0.1 --port 8897 \
      >"$RUNTIME_DIR/backend.log" 2>&1 &
    echo $! >"$RUNTIME_DIR/backend.pid"
  )
fi

if [[ -f "$RUNTIME_DIR/frontend.pid" ]] && kill -0 "$(cat "$RUNTIME_DIR/frontend.pid")" 2>/dev/null; then
  echo "前端已经运行。"
else
  (
    cd "$PROJECT_DIR/frontend"
    npm install
    nohup npm run dev -- --host 127.0.0.1 \
      >"$RUNTIME_DIR/frontend.log" 2>&1 &
    echo $! >"$RUNTIME_DIR/frontend.pid"
  )
fi

ready=false
for _ in {1..30}; do
  if curl -fsS http://127.0.0.1:8897/health >/dev/null 2>&1 && \
     curl -fsS http://127.0.0.1:5177/ >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 1
done

if [[ "$ready" != "true" ]]; then
  echo "服务启动超时，请运行 scripts/status.sh 查看日志。" >&2
  exit 1
fi

echo "启动完成："
echo "  网页：http://127.0.0.1:5177"
echo "  后端：http://127.0.0.1:8897"
echo "  日志：$RUNTIME_DIR"
echo "请保持此终端窗口打开；需要停止时可在另一终端运行 scripts/stop.sh。"

backend_pid="$(cat "$RUNTIME_DIR/backend.pid")"
frontend_pid="$(cat "$RUNTIME_DIR/frontend.pid")"
trap 'kill "$backend_pid" "$frontend_pid" 2>/dev/null || true' INT TERM EXIT
while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 2
done

echo "检测到服务进程退出，请运行 scripts/status.sh 查看日志。" >&2
exit 1
