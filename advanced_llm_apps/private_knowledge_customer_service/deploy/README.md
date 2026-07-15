# 本地部署说明

`docker-compose.yml` 只运行 PostgreSQL + pgvector。后端、前端和 Ollama 直接运行在当前 Mac，便于读取明确授权的本地文件夹并使用 Apple Silicon。

## 数据库

Compose 使用本机端口 `55433` 并创建三个数据库：

- `private_knowledge`：扫描元数据、标准片段和扫描记录。
- `private_knowledge_public`：公开 RAGLite 索引。
- `private_knowledge_sensitive`：敏感 RAGLite 索引。

`scripts/stop.sh` 只执行 `docker compose down`，不会删除 `deploy_pkcs_postgres_data` 数据卷。只有明确执行 `docker compose down -v` 才会删除数据，本项目脚本不会执行该操作。

## 环境配置

`deploy/.env.example` 是可提交的无秘密示例；首次运行会复制到项目根目录 `.env`。DeepSeek Key 只保存在本地 `.env`，健康检查和日志均不返回该值。

默认端口：

- Web：`127.0.0.1:5177`
- FastAPI：`127.0.0.1:8897`
- PostgreSQL：`127.0.0.1:55433`

本机代理环境必须保留 `NO_PROXY=localhost,127.0.0.1` 和小写 `no_proxy`，否则 LiteLLM 可能把 Ollama 请求错误地发送给代理。
