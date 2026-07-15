#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_DIR="$PROJECT_DIR/.runtime"
COMPOSE_FILE="$PROJECT_DIR/deploy/docker-compose.yml"

for service in frontend backend; do
  pid_file="$RUNTIME_DIR/$service.pid"
  if [[ -f "$pid_file" ]]; then
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid"
    fi
    rm -f "$pid_file"
  fi
done

docker compose -f "$COMPOSE_FILE" down
echo "服务已停止，PostgreSQL 数据卷已保留。"
