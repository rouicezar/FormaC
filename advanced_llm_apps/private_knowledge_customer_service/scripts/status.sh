#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_DIR="$PROJECT_DIR/.runtime"
COMPOSE_FILE="$PROJECT_DIR/deploy/docker-compose.yml"

for service in backend frontend; do
  pid_file="$RUNTIME_DIR/$service.pid"
  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "${service}：运行中，进程 $(cat "$pid_file")"
  else
    echo "${service}：未运行"
  fi
done

docker compose -f "$COMPOSE_FILE" ps

for log in backend frontend; do
  log_file="$RUNTIME_DIR/$log.log"
  if [[ -f "$log_file" ]]; then
    echo "${log} 最近日志："
    tail -n 12 "$log_file"
  fi
done
