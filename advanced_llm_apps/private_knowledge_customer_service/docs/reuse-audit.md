# awesome-llm-apps 复用审计

日期：2026-07-15

## 结论

本系统必须是 `awesome-llm-apps` 内既有模板的组合与增量改造，不再平行开发仓库已经具备的 RAG、问答、引用、模型客户端或前端能力。

推荐主体：

- 产品外壳与问答体验：`rag_tutorials/multimodal_agentic_rag`
- 混合检索与重排：`rag_tutorials/local_hybrid_search_rag`
- PostgreSQL + pgvector 知识库模式：`rag_tutorials/autonomous_rag`
- Ollama 本地模型与本地 Embedding：`rag_tutorials/agentic_rag_embedding_gemma`
- DeepSeek OpenAI 兼容调用：`advanced_ai_agents/single_agent_apps/ai_system_architect_r1`
- 客服记忆模式（后续阶段）：`advanced_ai_agents/single_agent_apps/ai_customer_support_agent`

## 复用矩阵

| 能力 | 仓库现有实现 | 复用方式 | 当前代码处理 |
| --- | --- | --- | --- |
| React + Vite 产品外壳 | `multimodal_agentic_rag/frontend` | 直接复制其工程、布局、问答区、状态区和引用列表，再删减不需要的上传与 3D 功能 | 不再新建另一套前端框架 |
| FastAPI 问答 API 形态 | `multimodal_agentic_rag/backend/server.py` | 适配复用 `/health`、`/space`、`/ask` 的请求/响应契约和线程池边界 | 将现有扫描 API 合并进该服务，不另起第二个后端 |
| 引用证据包 | `MultimodalRagStore.retrieval_payload()` | 适配复用 `citation/source/similarity/evidence` 结构，增加路径与页码定位 | 替换计划中自创的另一套证据格式 |
| 混合检索 | `local_hybrid_search_rag.perform_search()` | 直接调用 RAGLite `hybrid_search`、`retrieve_chunks` | 取消自写融合算法计划 |
| 重排 | `local_hybrid_search_rag` 的 Reranker/RAGLite | 直接调用 `rerank_chunks`，本地运行 | 取消自写重排器计划 |
| PostgreSQL + pgvector | `autonomous_rag` 的 `PgVector` 模式 | 复用 pgvector 作为持久向量层的模式；保留已完成的真实迁移和事务测试 | 已新增的权限/扫描元数据表保留，因为模板没有这些业务字段 |
| Ollama 本地模型 | `agentic_rag_embedding_gemma` | 复用 Agno `Ollama` / `OllamaEmbedder` 配置方式 | 不直接手写 Ollama HTTP 协议 |
| DeepSeek 云端模型 | `ai_system_architect_r1` | 复用 `OpenAI(base_url="https://api.deepseek.com")` 调用方式 | 仅增加统一适配层和隐私网关，不重写客户端 |
| 文件上传 | 多个模板已有 | 不采用 | 用户明确要求只读授权本地文件夹 |
| 本地目录增量扫描 | 仓库未找到满足新增/修改/删除与恢复语义的实现 | 必要新增 | 保留现有 inventory、fingerprint、scan service |
| 六类带定位解析 | 现有模板多为 PDF 或上传式解析，未覆盖六类和统一定位 | 必要新增 | 保留现有解析器，但后续把片段交给 RAGLite，而非另写检索引擎 |
| `public` / `sensitive` 权限 | 仓库现有 RAG 模板未提供 | 必要新增 | 保留分区元数据与检索前权限路由 |
| 敏感内容云端开关 | 仓库现有模板未提供 | 必要新增 | 新增隐私决策层，但模型调用复用现有客户端方式 |
| 人工客服接管 | 客服模板只提供记忆，未提供本目标所需接管状态机 | 当前目标不做 | 延后到飞书客服阶段 |

## 对当前实现的处置

### 保留

- `app/ingestion/inventory.py` 与 `fingerprint.py`
- 六类解析器和定位元数据
- 增量扫描与事务替换语义
- PostgreSQL 业务元数据、权限字段和真实持久化测试

这些能力在仓库模板中不存在完整等价实现，是系统相对模板的必要增量。

### 替换或收敛

- 不执行原 Task 6 中“自写向量检索、融合与重排”的方案，改为接入 RAGLite 现有函数。
- 不从零搭建 React 页面，直接以 `multimodal_agentic_rag/frontend` 为工程基线。
- 不自写 DeepSeek/Ollama 网络客户端，复用仓库现有 OpenAI-compatible 和 Agno/Ollama 用法。
- 统一采用 `multimodal_agentic_rag` 已有问答与引用响应结构。

### 删除

- 当前尚未产生自写检索、重排、模型或前端业务代码，因此无需删除这些未开始模块。
- 后续若适配过程中出现与模板等价的重复代码，必须在同一提交中移除。

## 最小闭环的新组合

```text
现有 multimodal_agentic_rag React UI
  -> 适配后的 FastAPI /health /space /ask
  -> 本项目新增的身份与隐私路由
  -> 现有 RAGLite hybrid_search + retrieve_chunks + rerank_chunks
  -> 现有 DeepSeek OpenAI-compatible 或 Agno Ollama 模型
  -> 本项目新增的本地目录增量扫描
  -> PostgreSQL + pgvector
```

## 审计门禁

后续每个功能开始前必须先在仓库中执行关键词和依赖检索，并在提交说明中标注复用来源。只有当矩阵确认“仓库不存在满足边界的实现”时，才允许新增模块。
