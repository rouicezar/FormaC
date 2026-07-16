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
| `channels/feishu` | 回调验证、事件去重、身份映射、纯文本协议 |
| `ingestion` | 文件发现、指纹、解析、分块、增量索引 |
| `retrieval` | 权限过滤、混合召回、重排、证据包 |
| `model_providers` | DeepSeek/OpenAI-compatible 与 Ollama 适配器 |
| `privacy` | 敏感内容与模型目标的发送决策 |
| `customer_service` | 风险规则、置信度、工单、接管状态 |
| `scheduler` | 每隔一天扫描及失败告警 |
| `audit` | 设置变更、访问、回答、接管和异常审计 |

## 4. 前端信息架构

### 管理后台

- `/admin/login`：本地超级管理员安全入口。
- `/admin/dashboard`：查询与问答分列统计、文件、索引和依赖健康度。
- `/admin/knowledge`、`/admin/knowledge/scan-detail`：公开/敏感目录、文件状态、手动扫描和异常诊断。
- `/admin/models`：云端与本地模型、连接测试、敏感云端开关。
- `/admin/users`：绑定用户、外部身份、内部授权和降级管理。
- `/admin/records`、`/admin/analytics`：全局查询/问答记录与分项分析。
- `/admin/shortcuts`：公开与内部快捷模板管理。
- `/admin/feishu`：飞书凭证、回调状态与纯文本协议配置。
- `/admin/audit`：关键设置、身份和隐私操作审计。
- `/admin/retrieval-lab`：身份模拟、召回、重排、权限过滤、上下文和答案调试。

### 用户端

- `/app/home`：动态身份、可见范围、原文查询与知识问答双入口。
- `/app/search`：不调用模型的原文查询及定位结果。
- `/app/chat`：基于证据的知识问答、引用和隐私降级状态。
- `/app/shortcuts`、`/app/history`：个人高频入口、查询/问答次数和历史。
- `/app/documents`：授权范围内的只读文档列表与预览。
- `/app/bind-feishu`、`/app/profile`：飞书绑定、历史合并确认和个人身份信息。
- 匿名、外部和内部用户使用同一套界面，由服务端强制决定知识范围；普通用户看不到检索分数或敏感元数据。

### 飞书端

- 私聊文本支持 `查询：`、`问答：`、`历史` 和 `帮助`，无前缀文本默认进入问答流程。
- 群聊只响应 `@机器人` 或工单交互事件。
- 用户侧只返回纯文本结论或原文及引用，不使用菜单或卡片。

## 5. 核心数据模型

- `knowledge_sources`：路径、分区、哈希、解析器版本、索引状态。
- `document_chunks`：正文、向量、关键词字段、页码/工作表/幻灯片定位。
- `scan_runs`：触发方式、统计、耗时和错误摘要。
- `user_identities`：飞书用户 ID、绑定状态、外部/内部身份、授权操作者和变更时间。
- `conversations` / `messages`：渠道、参与者、状态、模型和引用。
- `handoff_tickets`：触发原因、摘要、负责人、接管状态和解决结果。
- `model_configs`：非秘密配置和秘密引用，不保存明文 API Key。
- `audit_events`：主体、动作、对象、结果、时间和必要的非敏感差异。

## 6. 关键数据流

### 文件扫描

扫描器先验证根目录和两个固定子目录，再生成文件清单与指纹。新增或变更文件进入解析队列，解析结果在事务中替换旧片段；确认删除的文件先标记失效，再清理其索引。每次运行写入扫描报告。

### 问答

认证层解析用户身份，权限层生成允许分区；检索查询必须携带分区过滤条件。重排后形成包含来源定位的证据包。隐私策略根据证据分区、模型位置和敏感开关选择 `GENERATE`、`EXCERPT_ONLY` 或 `HANDOFF`。生成模型只能收到策略批准的证据包。

### 原文查询

`POST /search` 直接调用与问答共用的 RAGLite 检索器，输入查询词、服务端身份和结果上限，输出原文证据包。原文查询服务不持有模型注册表、模型提供商或隐私生成网关，因此不存在调用模型的执行路径。匿名和外部身份固定映射为 `external`，只能查询 public 物理库；只有服务端确认的内部身份才能查询 public 与 sensitive。

### 人工接管

用户请求、风险规则或低置信度创建工单。会话进入 `HUMAN_OWNED` 后，所有自动回复被状态机拦截。客服关闭或恢复后才进入 `BOT_ACTIVE`。

### 管理配置

`GET /admin/config` 只返回可公开的本地路径、模型名称、端点、当前提供商、敏感云端策略和密钥是否已配置，不返回密钥正文。`PUT /admin/config` 把可编辑字段原子写入权限为 `0600` 的本地配置覆盖文件，并把知识根目录和模型插件立即应用到当前运行时。`public/` 与 `sensitive/` 始终由知识根目录派生，管理员不能配置任意平行分区。敏感云端策略从关闭改为开启时，接口要求显式二次确认；普通 `/ask` 请求中的同名字段不具备授权效力。

### 飞书身份与内部授权

`identity_whitelist` 同时保存已登记的飞书身份和内部授权状态：`active=false` 表示已绑定的外部用户，`active=true` 表示管理员明确授权的内部用户。`POST /admin/users` 只创建外部身份；`PUT /admin/users/{id}/role` 执行提权或降级；`GET /admin/users/audits` 返回真实身份审计。绑定、提权和降级在同一数据库事务中写入 `audit_events`。身份解析遇到未知飞书 ID 或数据库查询失败时固定返回外部用户。身份仓储每次请求使用独立 SQLAlchemy Session，允许用户列表与审计并发读取。

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

## 9. 前端语言规范

- 复用 `multimodal_agentic_rag/frontend` 的布局与交互结构，但所有用户可见文案统一改为简体中文。
- 根文档使用 `lang="zh-CN"`；按钮、状态、错误、确认、空状态和 `aria-label` 必须同步中文化。
- 产品名、模型名和文件原文不强制翻译；它们不计为英文界面残留。
- 前端构建前执行中文界面检查，禁止模板中的英文演示文案重新进入产品页面。
