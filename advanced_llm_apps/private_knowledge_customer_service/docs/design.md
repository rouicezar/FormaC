# 私有知识库客服系统设计

## 1. 设计原则

- 默认安全：未知身份按外部客户、敏感云端发送默认关闭。
- 证据优先：检索只产生标准证据包，回答和引用使用同一份证据。
- 渠道解耦：知识库与客服引擎不依赖飞书，后续可增加企业微信或网页客服。
- 模型解耦：业务层不依赖 DeepSeek、Ollama 或任何特定 SDK。
- 失败可见：扫描、解析、模型、消息和人工接管均可审计。

## 2. 系统边界

```text
授权本地目录
  -> 扫描与解析
  -> 本地索引和元数据
  -> 权限过滤
  -> 混合检索与重排
  -> 隐私策略
  -> 模型生成或原文返回
  -> Web / 飞书
  -> 人工接管
```

后端使用 FastAPI。管理后台和问答端使用同一个 React + TypeScript 工程，通过路由和角色权限分隔。PostgreSQL + pgvector 保存业务数据、向量和全文索引；本地进程执行文档解析、Embedding 和重排。部署默认面向单台 Apple Silicon Mac，同时保留容器化组件边界。

## 3. 后端模块

| 模块 | 职责 |
| --- | --- |
| `api` | 管理、问答、认证、健康检查 API |
| `channels/feishu` | 回调验证、事件去重、身份映射、消息卡片 |
| `ingestion` | 文件发现、指纹、解析、分块、增量索引 |
| `retrieval` | 权限过滤、混合召回、重排、证据包 |
| `model_providers` | DeepSeek/OpenAI-compatible 与 Ollama 适配器 |
| `privacy` | 敏感内容与模型目标的发送决策 |
| `customer_service` | 风险规则、置信度、工单、接管状态 |
| `scheduler` | 每隔一天扫描及失败告警 |
| `audit` | 设置变更、访问、回答、接管和异常审计 |

## 4. 前端信息架构

### 管理后台

- `/admin/dashboard`：文件、索引、问答、工单与依赖健康度。
- `/admin/knowledge`：公开/敏感目录、文件状态、错误和手动扫描。
- `/admin/retrieval-lab`：问题、身份模拟、召回、重排、上下文和答案。
- `/admin/support`：会话队列、工单详情、人工回复与恢复机器人。
- `/admin/identities`：飞书用户白名单和变更记录。
- `/admin/models`：模型提供商、连接测试、敏感云端开关。
- `/admin/integrations/feishu`：应用凭证状态、回调与客服群配置。
- `/admin/audit`：筛选、查看和导出审计事件。

### 网页问答端

- `/chat`：会话列表、消息流、引用抽屉、原文模式、反馈和转人工。
- `/login`：飞书 OAuth 与本地账号登录。
- 员工和外部客户使用同一界面，但服务端决定可见知识范围。
- 管理员可打开检索调试抽屉，普通用户永远看不到内部分数或敏感元数据。

### 飞书端

- 私聊消息直接进入问答流程。
- 群聊只响应 `@机器人` 或工单交互事件。
- 客户回答卡片包含引用、未解决和转人工操作。
- 内部客服群接收工单卡片，并可接管、回复、关闭或恢复机器人。

## 5. 核心数据模型

- `knowledge_sources`：路径、分区、哈希、解析器版本、索引状态。
- `document_chunks`：正文、向量、关键词字段、页码/工作表/幻灯片定位。
- `scan_runs`：触发方式、统计、耗时和错误摘要。
- `identity_whitelist`：飞书用户 ID、本地账号映射、操作者和有效期。
- `conversations` / `messages`：渠道、参与者、状态、模型和引用。
- `handoff_tickets`：触发原因、摘要、负责人、接管状态和解决结果。
- `model_configs`：非秘密配置和秘密引用，不保存明文 API Key。
- `audit_events`：主体、动作、对象、结果、时间和必要的非敏感差异。

## 6. 关键数据流

### 文件扫描

扫描器先验证根目录和两个固定子目录，再生成文件清单与指纹。新增或变更文件进入解析队列，解析结果在事务中替换旧片段；确认删除的文件先标记失效，再清理其索引。每次运行写入扫描报告。

### 问答

认证层解析用户身份，权限层生成允许分区；检索查询必须携带分区过滤条件。重排后形成包含来源定位的证据包。隐私策略根据证据分区、模型位置和敏感开关选择 `GENERATE`、`EXCERPT_ONLY` 或 `HANDOFF`。生成模型只能收到策略批准的证据包。

### 人工接管

用户请求、风险规则或低置信度创建工单。会话进入 `HUMAN_OWNED` 后，所有自动回复被状态机拦截。客服关闭或恢复后才进入 `BOT_ACTIVE`。

## 7. 安全与异常处理

- 服务端强制权限过滤，前端隐藏不是安全边界。
- 云端请求使用可测试的策略网关，禁止模型适配器直接读取数据库。
- 飞书事件按事件 ID 幂等；回调快速确认，耗时工作异步执行。
- 模型失败时返回可靠原文或转人工，不回退到无证据自由回答。
- 新索引构建失败时继续使用旧版本，并向管理员展示失败状态。
- 日志禁止记录 API Key、完整敏感片段和飞书凭证。

## 8. 模板复用边界

- 直接以 `rag_tutorials/multimodal_agentic_rag/frontend` 作为 Web 产品工程基线，并适配复用其 FastAPI `/health`、`/space`、`/ask` 契约及引用响应结构。
- 直接调用 `rag_tutorials/local_hybrid_search_rag` 已使用的 RAGLite `hybrid_search`、`retrieve_chunks` 与 `rerank_chunks`，禁止重新实现融合和重排算法。
- 复用 `rag_tutorials/autonomous_rag` 的 PostgreSQL + pgvector 知识库存储模式。
- 复用 `rag_tutorials/agentic_rag_embedding_gemma` 的 Agno Ollama/OllamaEmbedder 配置方式。
- 复用 `advanced_ai_agents/single_agent_apps/ai_system_architect_r1` 的 DeepSeek OpenAI-compatible 调用方式。
- 参考 `advanced_ai_agents/single_agent_apps/ai_customer_support_agent` 的客服会话记忆。
- 参考 `voice_ai_agents/customer_support_voice_agent` 的知识客服流程，但首版不引入语音。
- 参考 `always_on_agents/always_on_hn_briefing_agent` 的定时任务、幂等和安全默认。
- 不直接复制演示应用的内存存储、硬编码模型或 Streamlit 单体结构。
- 详细复用与新增边界见 [复用审计](reuse-audit.md)。
