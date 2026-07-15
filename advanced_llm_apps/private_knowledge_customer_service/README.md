# 私有知识库客服系统

基于本仓库现有 RAGLite、`multimodal_agentic_rag` 前端、DeepSeek OpenAI-compatible 和 Agno Ollama 模板重组的本地私有知识库最小闭环。

当前可在 macOS Apple Silicon 上手动运行：读取授权的 `public/` 与 `sensitive/` 本地目录，解析 PDF、DOCX、Markdown、TXT、XLSX、PPTX，增量写入 PostgreSQL + pgvector，并通过简体中文网页执行权限隔离问答。

## 快速开始

前置条件：Docker Desktop、Ollama、uv、Node.js/npm。

```bash
cd advanced_llm_apps/private_knowledge_customer_service
./scripts/start.sh
```

首次启动会：

1. 从 `deploy/.env.example` 创建本地 `.env`。
2. 启动持久化 PostgreSQL + pgvector，并创建业务、公开索引、敏感索引三个数据库。
3. 检查并安装 `embeddinggemma:latest` 与 `qwen3:0.6b`。
4. 执行数据库迁移，启动 FastAPI 和复用改造后的 React 前端。

启动成功后打开：<http://127.0.0.1:5177>。

保持启动终端打开。另开终端可查看状态或停止：

```bash
./scripts/status.sh
./scripts/stop.sh
```

停止不会删除 PostgreSQL 数据卷。再次启动后，未变化文件会显示为“未变化”，可用于验证持久化。

## 配置

本地配置位于 `.env`，该文件不会提交 Git。默认知识目录是 `sample_knowledge/`：

```text
sample_knowledge/
├── public/       外部和内部身份均可检索
└── sensitive/    仅内部身份可检索
```

要读取自己的授权文件夹，把 `.env` 中的 `PKCS_KNOWLEDGE_ROOT` 改为包含上述两个子目录的路径，然后重新启动。

如需使用 DeepSeek，在 `.env` 中填写：

```dotenv
PKCS_DEEPSEEK_API_KEY=你的密钥
```

敏感云端开关默认关闭。关闭时，只要检索结果包含敏感片段，系统就不会调用 DeepSeek，而是直接返回带文件和位置的本地原文。

## 手动验收

完整步骤和预期结果见 [手动验收指南](docs/manual-acceptance.md)。

## 项目文档

- [需求](docs/requirements.md)
- [设计](docs/design.md)
- [项目状态](docs/project-status.md)
- [复用审计](docs/reuse-audit.md)
- [部署说明](deploy/README.md)

飞书、正式 OAuth、员工白名单管理、人工接管、隔日调度和完整管理后台不属于当前最小闭环。
