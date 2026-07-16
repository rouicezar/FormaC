# 项目状态

更新时间：2026-07-16

## 总体状态

私有知识库底层最小闭环已在当前 Mac 真实跑通；正式产品形态已冻结为管理员端与用户端两部分，当前进入基于 Stitch 冻结稿的真实前端重组阶段。现有三栏页面只保留为管理员检索实验室能力，不再作为最终用户产品形态。

## 里程碑

| 阶段 | 状态 | 验收点 |
| --- | --- | --- |
| 需求确认 | 已完成 | 用户、权限、知识来源、模型隐私、客服与前端范围已确认 |
| 架构设计 | 已完成 | 后端、前端、飞书、数据流和异常策略已记录 |
| 仓库重组 | 已完成 | 独立应用目录与正式入口已建立 |
| 阶段 1：扫描基础 | 已完成 | 真实 pgvector 迁移、六类解析、增量扫描、重连持久化和手动 API 已通过测试 |
| 阶段 2：本地检索 | 已完成 | 扫描新增/修改/删除已进入分区 RAGLite 索引，并返回可核查引用 |
| 阶段 3：模型插件 | 已完成 | DeepSeek/Ollama 可切换，敏感云端默认关闭且隔离策略可证明 |
| 阶段 4：检索实验 Web | 已完成 | 中文实验页面已真实点击扫描、公开问答、敏感原文与引用 |
| 正式 UI 设计冻结 | 已完成 | 42 个 Stitch 画板甄别为 28 个正式页面/状态，并按 `/app`、`/admin` 路由重组 |
| 正式产品前端第一阶段 | 已完成 | 正式路由、两套导航、动态身份、真实用户首页与管理首页已进入现有 React 工程 |
| 正式产品前端第二阶段 | 已完成 | 独立原文查询 API、正式查询页与知识问答页已完成真实联调和设计 QA |
| 正式产品前端第三阶段 | 已完成 | `/admin/knowledge`、`/admin/models`、配置读写 API、手动扫描与服务端敏感云端策略已真实联调 |
| 正式产品前端第四阶段 | 已完成 | `/admin/users`、飞书身份默认外部、内部提权、即时降级与身份审计已真实联调 |
| 阶段 5：飞书纯文本通道 | 已完成（待真实租户验收） | 管理配置、验签、令牌、去重、私聊/群聊 @、四类命令、异步回复与身份权限 |
| 正式产品前端第六阶段 | 已完成 | `/admin/records` 统一展示 Web 与飞书查询/问答记录 |
| 最小闭环验收 | 已完成 | 一键启停、增删改、权限、隐私、引用和重启持久化已实测 |

## 当前决策

- 以 `multimodal_agentic_rag` 的前后端分层为基础进行独立重组。
- 知识原文留在本地授权目录，应用不提供上传。
- 匿名用户可使用公开查询和问答；飞书绑定成功后默认仍是外部用户，只有管理员明确授权后才是内部用户。
- 敏感内容发送给云端模型的开关默认关闭。
- 所有用户端和管理端 Web 界面必须完全使用简体中文；模型正式名称、文件名和原文除外。
- 原文查询不调用大模型；知识问答是基于检索证据的总结或汇总，两者独立记录和统计。
- 飞书只使用纯文本查询和问答，不使用菜单或消息卡片。

## 2026-07-15 正式 UI 设计冻结

- 已完整检查用户导出的 42 个 Stitch 画板及 HTML，保留 28 个有独立业务价值的页面/状态，删除 14 个重复、旧版或违反业务规则的版本。
- 28 个正式状态均保留 HTML；其中 25 个有有效截图，3 个导出的 `screen.png` 实为图片拉取失败占位文本，已删除并在冻结清单标注。
- 保留稿已重组到 `docs/ui/stitch/stitch_coreknowledge/app/` 与 `admin/`，并以正式路由和状态命名。
- 已建立 `docs/ui/stitch/stitch_coreknowledge/README.md`，记录正式画板映射、删除清单，以及英文侧栏、上传按钮、固定身份和错误模型描述等必须修正的残留。
- 正式产品重组设计见仓库 `docs/plans/2026-07-15-coreknowledge-product-restructure-design.md`。
- Stitch 的 `screen.png` 是视觉依据，`code.html` 只作为布局和样式参考；正式实现继续使用现有 React 工程与已跑通 API。

## 2026-07-15 正式产品前端第一阶段

- 已在应用根目录新增 `AGENTS.md`，固化禁止一次性预览、必须复用仓库能力、查询与问答分离、身份权限、零上传、敏感云端边界、全中文和飞书纯文本等铁律。
- 已在现有 React 工程引入 React Router，建立 `/app/*` 与 `/admin/*` 正式路由及两套独立导航，没有创建平行前端。
- 已新增动态身份上下文：默认匿名访客，只能访问公开知识；本地状态只接受匿名、外部与内部三种服务端语义，飞书绑定入口不会自动显示内部身份。
- `/app/home` 已按冻结稿实现动态身份、知识范围、原文查询与知识问答双入口、真实空历史和快捷入口说明。
- `/admin/dashboard` 已按冻结稿实现管理导航、查询/问答分项指标、真实后端健康状态和快捷管理。没有真实接口的统计明确显示“待接入”，未使用虚构数据。
- 现有三栏检索实验台未重写，已迁移为 `/admin/retrieval-lab`；其他正式路由已建立阶段占位页并明确说明后续接入真实 API。
- 已通过 TypeScript 与 Vite 生产构建；真实浏览器验证用户首页、管理首页刷新、控制台零错误，以及 390 × 844 无横向溢出。
- 设计对照报告见 `design-qa.md`，桌面、移动实现截图和 Stitch 并排对照保存在 `docs/ui/`。

## 2026-07-15 正式产品前端第二阶段

- 已新增独立 `POST /search`：只持有并调用现有 RAGLite 检索器，不持有模型注册表或模型提供商，从结构上禁止原文查询调用模型。
- `/search` 复用问答使用的同一检索器与标准证据包，保留 public/sensitive 物理分区、身份过滤、混合检索、重排和文件定位，没有重新实现检索算法。
- 新增 4 项原文查询 API 测试，覆盖无模型配置正常返回、默认外部身份、内部身份与结果上限传递、空结果和服务未配置。
- `/app/search` 已实现默认、加载、结果、原文预览、无结果和错误状态；结果明确显示“未调用模型”。
- `/app/chat` 已接通现有 `/ask`，支持 Ollama/DeepSeek 选择、知识库回答、引用、证据不足、错误和敏感云端 `excerpt_only` 降级状态。
- 真实联调：`/search` 返回 `public/退款政策.md` 三条原文及行号；`/ask` 通过 Ollama 回答“七个自然日”并返回三条引用。
- 浏览器已验证查询提交、结果选择、原文预览、问答生成、引用侧栏和控制台零错误；390 × 844 两页均无横向溢出。
- 第二阶段桌面/移动截图及 Stitch 并排对照保存在 `docs/ui/`，最新结论追加在 `design-qa.md`。

## 2026-07-15 简体中文界面检查

- 当前后端可保存和解析中文内容，解析器测试已包含中文锚点。
- 初次检查发现复用的 `multimodal_agentic_rag/frontend` 基线仍有英文标题、表单、状态、错误、空状态和无障碍标签，当时不能判定为完整中文支持。
- 已将当前基线的用户可见静态文案和无障碍标签改为简体中文，并把根文档语言改为 `zh-CN`；模型正式名称、文件名和协议标识保留原文。
- 已将用户可见文案零英文残留加入需求、设计、实施步骤与后续前端回归门禁。
- 当前中文基线已通过 TypeScript 与 Vite 生产构建；后续扫描/模型/隐私界面同样必须遵守此门禁。
- 后续只改造这一套复用前端，不新建平行中文前端。

## 2026-07-15 RAGLite 适配检查点

- 已新增薄适配层，直接调用模板中的 `hybrid_search`、`retrieve_chunks` 和 `rerank_chunks`，未实现替代检索或重排算法。
- public 与 sensitive 使用独立检索存储；契约测试证明外部身份只调用 public 存储。
- 引用响应复用 `citation/source/similarity/evidence`，并增加分区和页码/工作表/幻灯片定位。
- 当前后端完整回归：40 项通过，包含真实 PostgreSQL、pgvector 与 Ollama 集成测试。

## 2026-07-15 RAGLite 真实运行验证

- 已安装仓库模板固定使用的 `raglite==0.2.1`；为兼容当前 Python 3.12，明确约束 NumPy、Numba 与 llvmlite 的兼容版本，并补齐 RAGLite 官方 pandoc 扩展和 spaCy 多语言分句模型。
- 已复用 `agentic_rag_embedding_gemma` 指定的 Ollama `embeddinggemma:latest`，模型已在本机安装；索引和查询均未把文档发送到云端。
- 已在现有 pgvector 测试容器中建立 `pkcs_public_rag` 与 `pkcs_sensitive_rag` 两个物理隔离数据库。
- 已把中文公开样本真实写入 `pkcs_public_rag`，并用“客户几天内可以退款？”执行 RAGLite `hybrid_search`、`retrieve_chunks` 与 `rerank_chunks` 调用链，成功召回“七个自然日”原文。
- 本机代理会影响 LiteLLM 访问 Ollama；本地运行配置必须包含 `NO_PROXY=localhost,127.0.0.1`。
- 扫描事务已连接 RAGLite 写入器：业务元数据成功后才提交新索引，并在失败时回滚新索引；删除文件时先移除检索内容，避免敏感文档残留。
- 真实集成测试已验证公开与敏感物理分库、外部只检索公开内容、内部可检索敏感内容，以及新增、修改、删除后的检索结果同步变化。
- 已处理 RAGLite 0.2.1 查询空数据库时的已知异常：调用其原有检索链前仅检查是否存在片段，不替代检索或重排算法。
- 真实集成测试验证 TXT 引用包含行号定位；六类解析器已有页码、段落、工作表和幻灯片定位回归测试。

## 2026-07-15 执行检查点

- 已建立 FastAPI 后端和不暴露秘密的健康检查。
- 已建立 9 张核心表、pgvector 字段与 Alembic 初始迁移。
- Alembic 离线 SQL 验证通过；随后已完成真实 pgvector 迁移与持久化验证，见下方记录。
- 已完成授权根目录校验、`public/` / `sensitive/` 分区、六类扩展名过滤、SHA-256 文件指纹和符号链接越界防护。
- 当前后端测试：12 项通过。
- 当前分支：`feature/private-knowledge-phase-1`。

## 2026-07-15 Task 4–5 检查点

- PDF、DOCX、Markdown、TXT、XLSX、PPTX 均通过真实合成文件解析测试。
- 标准片段保留页码、段落、行号、工作表或幻灯片定位。
- 增量扫描已覆盖首次新增、未变化跳过、内容更新、文件删除和单文件失败。
- 模拟事务替换失败时，旧内容哈希和旧片段保持不变。
- 已增加 `POST /admin/scans` 与 `GET /admin/scans/{id}`。
- SQL 仓储把扫描结果写入 `scan_runs`；该项随后已在真实 pgvector 数据库完成集成测试，见下方验证记录。
- 当前后端测试：25 项通过；Python 编译检查通过。

## 2026-07-15 真实 pgvector 验证

- 已在隔离容器 `pkcs-test-db`（本机端口 `55432`）真实执行 Alembic `0001` 迁移。
- 已确认 `vector` 扩展和 9 张业务表实际存在。
- 真实测试覆盖首次扫描、关闭并重建数据库会话、读取持久化片段、更新文件、删除文件和扫描报告持久化。
- 首轮测试发现更新时新旧片段唯一键冲突；已修复为保存点内先删除并 flush，再插入。
- 修复后真实 PostgreSQL 集成测试：2 项通过。

## 2026-07-15 复用路线校正

- 用户再次明确：仓库已有能力不得重复开发，本系统必须基于现有模板搭建。
- 审计确认此前对模板主要是“参考”，复用强度不足；已停止原 Task 6 的自写检索方案。
- Web 工程改为直接采用 `multimodal_agentic_rag/frontend` 基线。
- 混合检索与重排改为直接适配 `local_hybrid_search_rag` 使用的 RAGLite 函数。
- DeepSeek 与 Ollama 调用分别复用仓库现有 OpenAI-compatible 和 Agno 模式。
- 目录增量扫描、六类定位解析、公开/敏感权限与隐私开关属于模板缺失能力，继续保留。
- 复用矩阵见 `docs/reuse-audit.md`。

## 2026-07-15 模型与隐私检查点

- DeepSeek 适配器直接复用仓库 `ai_system_architect_r1` 的 OpenAI-compatible 客户端与 `https://api.deepseek.com` 端点，不自写网络客户端。
- Ollama 适配器直接复用仓库 `agentic_rag_embedding_gemma` 的 Agno `Ollama` 模型模式；运行依赖按原模板补入 `agno` 与 `ollama`。
- `/ask` 已支持测试身份、模型提供商和 `allow_sensitive_cloud`；该开关请求默认值为 `false`。
- 策略测试证明：内部身份检索到敏感证据、选择云端且开关关闭时，不调用云端提供商，只返回带定位的本地原文；外部身份遇到敏感证据时服务端拒绝。
- 无检索证据时不调用任何模型，避免脱离知识库自由回答。
- 运行时已能从环境变量组装业务数据库、公开/敏感 RAGLite 数据库、扫描器、检索器与模型注册表；未配置 DeepSeek API Key 时只注册 Ollama。
- 已在本机安装 `qwen3:0.6b`，并通过 Agno `Ollama` 适配器真实生成“本地模型已连接。”，确认本地中文回答链路可用。
- 当前完整后端回归：57 项通过，包含真实 PostgreSQL、pgvector 与 Ollama 嵌入集成测试。

## 2026-07-15 最小 Web 页面检查点

- 继续使用已复制的 `multimodal_agentic_rag/frontend` React + Vite 工程、三栏布局、问答区和引用区，没有新建平行前端。
- 已移除模板中的上传、网页地址和三维向量演示交互，改为本地目录说明、手动增量扫描、扫描统计、外部/内部测试身份、DeepSeek/Ollama 选择、敏感云端开关、问答与引用定位。
- 所有用户可见静态文案、空状态、错误提示和无障碍标签均为简体中文；保留的英文仅限 PostgreSQL、pgvector、public、sensitive、Ollama、DeepSeek 等正式名称或目录名。
- 已通过 TypeScript 与 Vite 生产构建，并在真实浏览器以桌面视口检查三栏布局；默认状态为外部身份、Ollama 本地模型、敏感云端开关关闭且禁用。
- 已增加 `localhost:5177` CORS 回归测试，确保当前 Vite 端口可以调用 FastAPI。
- 已在真实浏览器完成前后端联调：页面显示“后端已连接”，点击扫描显示 2 个未变化文件，公开问答返回“七个自然日”及 `public/退款政策.md` 行号引用。
- 已在页面切换内部身份与 DeepSeek，保持敏感云端开关关闭，成功进入“原文模式”并显示 `sensitive/内部折扣规则.md`、八五折原文与行号；未配置 DeepSeek Key，证明该路径没有调用云端。

## 2026-07-15 长时阅读配色优化

- 用户明确否定原来的纯黑底、橙色高亮和发光渐变，认为伤眼且有明显 AI 演示页风格。
- 保留已经验收的三栏布局和全部交互，仅重做视觉系统：暖灰页面、米白内容卡、墨绿色主操作、柔和蓝灰与沙金状态色。
- 已移除纯黑背景、荧光橙、强渐变、发光效果和技术感背景网格；正文改为深灰绿而非纯黑，边框和状态底色降低对比。
- 已在真实浏览器复核桌面首屏，可读层级、默认隐私开关和三栏内容均正常；前端生产构建通过。

## 2026-07-15 最小闭环最终验收

- `scripts/start.sh` 已真实完成 PostgreSQL + pgvector 三库启动、Alembic 迁移、Ollama 模型检查、FastAPI 与 Vite 启动；`scripts/stop.sh` 已证明停止后保留数据卷，`scripts/status.sh` 可读取进程、容器和日志。
- 首次默认目录扫描：新增 2、失败 0；停止并重新启动后扫描：新增 0、未变化 2，公开与敏感索引仍可查询，证明服务重启后的业务元数据和两套 RAGLite 索引持久化。
- 临时公开文档真实验收：新增扫描 `added=1` 并回答“青松一号”；修改扫描 `updated=1` 并只召回“青松二号”；删除扫描 `deleted=1` 且后续引用不再出现该文件。临时文件已清理。
- 外部身份查询内部折扣时，返回引用全部属于 `public`，没有 `sensitive` 来源；内部身份可检索敏感来源。
- 敏感云端关闭时，在没有 DeepSeek Key 的情况下返回本地原文和引用；策略捕获测试同时证明云端提供商未收到请求。
- 本机已安装并真实调用 `embeddinggemma:latest` 与 `qwen3:0.6b`；Agno Ollama 中文生成链路、公开 RAG 问答均实测成功。
- 最终完整后端回归：60 项通过。前端 TypeScript + Vite 7.3.6 生产构建通过；`npm audit fix` 后安全审计为 0 个漏洞。
- 已提供 `.env` 示例、合成公开/敏感知识、Docker Compose、本地启停脚本和 `docs/manual-acceptance.md`。

## 2026-07-15 正式产品前端第三阶段

- `/admin/knowledge` 已替换占位页：读取真实知识根目录，明确派生 `public/` 与 `sensitive/`，保存后立即更新扫描服务，并调用已有 `POST /admin/scans` 展示新增、更新、删除、跳过、失败和错误。
- `/admin/models` 已替换占位页：读取和保存 DeepSeek、Ollama、当前模型插件与敏感云端策略；API Key 只写入本机 `0600` 配置文件，接口仅返回“是否已配置”。
- 新增 `GET/PUT /admin/config`。配置采用原子替换写入，运行中的扫描根目录和模型注册表同步更新，不重写已有扫描器、模型适配器或隐私网关。
- 敏感云端策略已收回服务端：普通 `/ask` 请求即使传入 `allow_sensitive_cloud=true` 也不能越权；从关闭改为开启时，前端弹窗与后端接口均强制二次确认。
- 真实浏览器完成路径保存、手动扫描（新增 0、更新 0、删除 0、跳过 2、失败 0）、策略弹窗取消、安全保存与控制台零错误验证。
- 桌面端完成冻结稿视觉抽查；390 × 844 下两个页面 `scrollWidth` 与 `clientWidth` 均为 390px，无横向溢出。
- 后端完整回归为 67 项通过、3 项因外部集成条件跳过；前端 TypeScript 与 Vite 生产构建通过。

## 2026-07-16 正式产品前端第四阶段

- 新增身份服务与 `GET/POST /admin/users`、`PUT /admin/users/{id}/role`、`GET /admin/users/audits`，复用已有 `identity_whitelist` 与 `audit_events` 表，没有新增平行身份库。
- 飞书身份首次绑定固定为外部用户；未知身份和身份查询失败也固定降级为外部用户。只有本地超级管理员显式操作才能提权为内部用户。
- 提权与降级均在服务端执行，并与审计事件同事务保存；降级后身份立即恢复为外部用户，后续只能获得公开知识范围。
- `/admin/users` 已替换占位页，接入真实用户总数、外部/内部分项、飞书身份列表、绑定弹窗、提权/降级确认和最近身份审计，不展示 Stitch 虚构活跃度或查询次数。
- 真实浏览器已完成专用测试身份 `ou_codex_acceptance_20260716` 的外部绑定、内部提权、外部降级和三条审计展示；控制台零错误。
- 浏览器首次并发读取暴露共享 SQLAlchemy Session 冲突，已改为每请求独立 Session，并用真实 PostgreSQL 验证跨仓储实例持久化。
- 390 × 844 下页面与视口宽度均为 390px，无页面级水平溢出；宽表只在自己的容器内横向滚动。
- 最终完整回归为 76 项通过、4 项因外部集成环境未注入而跳过；另有 1 项身份 PostgreSQL 集成测试在本机真实通过，前端生产构建通过。

## 2026-07-16 正式产品前端第五阶段

- `/admin/feishu` 已替换占位页，提供 App ID、App Secret、Verification Token、Encrypt Key 的真实读取/保存；密钥写入本机 `0600` 配置，读取 API 只返回配置状态。
- 新增 `POST /feishu/events`：完成 URL challenge、回调签名、Verification Token、事件类型和群聊 `@机器人` 校验；无关事件安全忽略。
- 新增 `查询：`、`问答：`、`历史`、`帮助` 纯文本协议；无前缀文本默认问答，不引入菜单和消息卡片。
- 通道复用既有身份服务：未知或失败身份固定降级为外部用户，内部用户才可检索敏感分区；问答固定关闭敏感内容云端发送。
- 新增 `feishu_events` 迁移，事件 ID 跨重启去重并持久化个人历史；回复通过后台任务获取租户令牌并调用飞书消息 reply 接口，重复事件不重复回发。
- 自动化回归为 83 项通过、4 项因外部集成环境未注入而跳过；另有 3 项 PostgreSQL 迁移、表结构和跨会话持久化测试在本机真实通过，前端 TypeScript 与 Vite 生产构建通过。
- 真实浏览器已验证正式配置页、纯文本协议与未配置状态；390 × 844 下页面宽度等于视口宽度且控制台零错误。
- 2026-07-16 已接入真实飞书测试应用凭据并修复加密回调：飞书 `encrypt` 外壳先按 `X-Lark-*` 头验签，再用 Encrypt Key 派生 AES-CBC 密钥解密，解密后校验 Verification Token；真实租户私聊发送“帮助”已收到机器人纯文本回复。
- 当前仅确认真实私聊帮助链路；群聊 `@机器人`、重复事件和内外身份范围仍待真实租户验收。

## 2026-07-16 正式产品前端第六阶段

- 新增 `interaction_records` 与 Alembic 迁移 `0003_interaction_records`，统一保存 Web 与飞书的原文查询、知识问答、请求身份、引用包和渠道元数据。
- Web `/search` 与 `/ask` 成功返回后写入统一记录；飞书 `查询：` 与 `问答：` 成功处理后也写入统一记录，同时保留 `feishu_events` 继续负责回调幂等与个人 `历史`。
- 新增 `GET /admin/records`，支持按 `web/feishu` 渠道与 `search/ask` 类型筛选，读取失败时明确显示“全局记录服务尚未配置”。
- `/admin/records` 已替换占位页，展示真实记录总数、网页来源、飞书来源、知识问答数量、请求方、身份、引用数与内容摘要，不使用虚构活跃数据。
- 自动化回归为 85 项通过、4 项因外部集成环境未注入而跳过；前端 TypeScript 与 Vite 生产构建通过。
- 当前已完成真实租户私聊“帮助”收发；群聊 `@机器人`、重复事件和内外身份范围收发验收仍未完成。

## 2026-07-16 DeepSeek 真实验收与隐私复验

- 已确认管理端保存的 DeepSeek API Key 生效；首次真实请求返回 DeepSeek 400，原因是本地模型名配置为过期的 `deepseek-flash`。
- 已将本地管理配置修正为 `deepseek-v4-flash`，并把代码默认 DeepSeek 模型从 `deepseek-chat` 更新为 `deepseek-v4-flash`，避免新环境继续使用不可用默认值。
- 真实公开知识问答验收通过：`POST /ask` 使用外部身份与 DeepSeek 返回 200，`mode=generate`，回答“七个自然日”并引用 `public/退款政策.md`。
- 敏感云端策略复验通过：管理员策略 `allow_sensitive_cloud=false` 时，即使请求体携带 `allow_sensitive_cloud=true`，服务端仍返回 `mode=excerpt_only` 和本地原文；自动化测试证明该路径不会调用云端提供商。
- 群聊 `@机器人` 因当前飞书账号缺少企业内部群权限，标记为外部权限阻塞，暂不阻塞普通用户端主线。
- 针对配置、问答、模型适配器和隐私策略的自动化回归为 22 项通过。

## 2026-07-16 普通用户端历史记录阶段

- 新增 `GET /app/records`，按 `requester_id` 返回当前用户自己的查询/问答记录，并给出个人总数、原文查询数、知识问答数、网页/飞书来源数和引用总数；`/admin/records` 仍保留全局视图。
- Web `/search` 与 `/ask` 现在写入前端传入的稳定浏览器 requester，不再全部落到 `web-anonymous`，为后续 Web/飞书身份合并保留映射点。
- `/app/history` 已替换占位页，展示当前身份、记录归属、个人统计、筛选、空状态和明细列表；普通用户看不到全局请求方列表、检索分数或管理员统计。
- 真实后端验收通过：`/app/records?requester_id=web-history-smoke` 初始为空，产生一次原文查询后只返回该 requester 的 1 条记录和 3 条引用统计。
- 真实浏览器验收通过：在 `/app/search` 查询“退款期限”后，`/app/history` 显示“我的记录 1 / 原文查询 1 / 知识问答 0 / 引用总数 3”，无英文占位文案。
- 自动化回归为 12 项后端记录、问答与原文查询测试通过；前端 TypeScript 与 Vite 生产构建通过。

## 2026-07-16 普通用户端身份映射阶段

- 新增 `GET /app/profile` 与 `POST /app/profile/bind-feishu`：用户端可读取当前浏览器 requester、飞书 open_id、外部/内部角色、可访问范围和个人记录统计。
- 用户端绑定飞书身份默认创建外部用户；管理员后续在 `/admin/users` 提权或降级后，`/app/profile` 会反映服务端真实授权结果。
- `/app/records` 支持同时传入浏览器 requester 与飞书 open_id，合并展示 Web 与飞书个人历史，但仍不会暴露全局记录。
- `/app/profile` 与 `/app/bind-feishu` 已替换占位页，显示身份映射、绑定状态、可访问范围和记录统计；真实 OAuth 接入前，飞书 open_id 手动输入用于验收 Web/飞书记录合并。
- 真实 HTTP 验收通过：匿名 profile 初始为公开知识范围；绑定 `ou_profile_smoke` 后默认外部用户，并保留 Web 记录统计。
- 真实浏览器验收通过：在 `/app/bind-feishu` 绑定 `ou_browser_profile_smoke` 后自动进入 `/app/profile`，页面显示外部用户、飞书 open_id 与公开知识范围，无英文占位文案。
- 当前知识库根目录已配置为用户本机测试知识库目录，后续普通用户完整验收将使用该目录。
- 自动化回归为 16 项身份、profile、记录和审计测试通过；前端 TypeScript 与 Vite 生产构建通过。

## 2026-07-16 测试知识库目录结构校验

- 尝试使用当时配置的测试知识库子目录做普通用户完整验收时，真实扫描返回 `knowledge root requires a real public/ directory`。
- 现场确认该目录下是业务分类目录，缺少产品铁律要求的固定 `public/` 与 `sensitive/` 子目录，因此外部公开查询/内部敏感访问完整验收暂不能继续。
- 已修复配置保存边界：`PUT /admin/config` 现在会拒绝不存在的知识库根目录，以及缺少 `public/` 或 `sensitive/` 的根目录，避免无效配置进入运行态。
- 真实 API 验收通过：保存缺少固定分区的测试知识库子目录被拒绝，返回“知识库根目录必须包含 public/ 子目录”。
- 自动化回归为 13 项配置、profile 和记录测试通过；前端 TypeScript 与 Vite 生产构建通过。

## 2026-07-16 真实知识库后台扫描阶段

- 用户已将测试知识库整理为固定 `public/` / `sensitive/` 根结构，并将后台配置切换到新的测试知识库根目录。
- 真实知识库当前包含数百个文件；旧版 `POST /admin/scans` 同步全量扫描会让请求长时间挂起，不适合作为普通用户完整验收前置动作。
- 已将手动扫描改为后台执行：`POST /admin/scans` 立即保存并返回 `status=running` 的扫描记录，扫描核心在后台继续执行，`GET /admin/scans/{id}` 查询状态和最终报告。
- 已补充扫描并发保护：已有运行中扫描时，重复触发会返回同一个 running 记录，避免并发重复索引同一知识库。
- 已修复后台扫描的数据库会话边界：生产 runtime 的扫描仓储改为基于 Engine 为每次操作创建独立 Session，避免后台线程复用主线程 SQLAlchemy Session。
- `/admin/knowledge` 已从同步扫描结果展示改为后台扫描状态轮询：运行中明确显示“后台扫描中”，完成后再展示新增、更新、删除、跳过和失败统计。
- 已补充运行中进度落库：每处理一个文件或删除项后更新扫描报告，避免页面长期显示 `running + 0` 被误判为扫描无效。
- 已修复本地运行脚本边界：`scripts/stop.sh` 现在会按项目路径清理残留后端/前端进程，`scripts/start.sh` 会拒绝在残留进程存在时重复启动，`scripts/status.sh` 会显示项目相关进程和监听端口，避免多后端进程造成扫描状态与日志不一致。
- 已扩展扫描状态可观测性：扫描报告现在返回 `total`、`processed`、`current_path`，大文件处理期间也能显示“已处理 N/总数”和当前文件，避免长时间只有计数不变。
- 真实 API 验收通过：触发手动扫描立即返回 `202 Accepted`、`status=running`；后台日志持续显示 embedding 与 chunks 插入推进。
- 真实 API 复验通过：新扫描启动后，`GET /admin/scans/{id}` 已能看到运行中计数从 0 增长到 `skipped=3`，证明前端轮询可展示实际进度。
- 干净重启复验通过：清理残留进程后仅一个后端监听 `8897`、一个前端监听 `5177`；重新触发扫描后同一个 run 从 0 推进到 `skipped=4`。
- 当前真实扫描复验通过：新 run 返回 `total=448`、`processed=5`、`current_path=public/01_RSS/horizon-2026-06-09-raw.md`，前端可展示具体进度与当前文件。
- 自动化回归为 24 项配置、profile、记录和扫描测试通过；前端 TypeScript 与 Vite 生产构建通过。
- 进一步排查发现：用户当前真实知识库包含大量 RSS 原文与长文档，全量扫描即使进入后台也会长时间处理前几个大文件，容易被误判为“扫描无法使用”。
- 已新增局部扫描能力：`POST /admin/scans?prefix=<相对路径或目录>` 只扫描匹配的文件/目录，且局部扫描不会执行删除对账，避免误删未扫描来源；`limit` 扫描同样不会误删未扫描来源。
- `/admin/knowledge` 已新增“扫描范围（可选）”输入框，可填 `public/12_长期关注/Anthropic news.md` 或 `public/09_视频口播稿/` 先验证链路，留空才执行全量扫描。
- Prefix 不匹配任何真实文件时，扫描报告现在明确返回 `status=failed` 和 `no files matched scan prefix`，不再静默显示 0 文件成功。
- 真实 API 验收通过：`prefix=public/missing.txt` 返回 failed；`prefix=public/12_长期关注/Anthropic news.md` 返回 `status=succeeded`、`total=1`、`processed=1`、`added=1`。
- 当前局部扫描自动化回归为 27 项通过；前端 TypeScript 与 Vite 生产构建通过。
- 针对大知识库扫描中断问题，已将 `/admin/knowledge` 的空范围扫描改为分批可恢复模式：每批默认处理最多 25 个新增或变化文件，批次完成后自动继续下一批；若服务或页面中断，再次点击会跳过已落库文件并继续剩余新增/变化文件。
- 新增 `changed_only` 扫描模式：后端先比较当前文件指纹与已存业务元数据，只挑选未索引或内容已变化的文件进入本批扫描；局部扫描和分批扫描都不会执行删除对账，避免中断时误删未扫描来源。
- 已补充向量写入进度心跳：RAGLite 写入每个 canonical chunk 后回写扫描报告，`current_path` 会显示类似 `public/...md · 向量写入 11/18`，避免单个长文档处理期间被误判为扫描中断。
- 真实恢复场景验收通过：重启服务中断旧扫描后，触发 `POST /admin/scans?limit=1&changed_only=true`，报告进入 `changed_only=true`、`total=1`，处理中显示 `向量写入 11/18`，最终返回 `status=succeeded`、`processed=1`、`added=1`。
- 当前扫描稳定性回归为 25 项通过；前端 TypeScript 与 Vite 生产构建通过。

## 2026-07-16 普通用户端真实闭环验收

- 真实公开检索通过：外部身份 `POST /search` 可从真实测试知识库返回 `public/...` 引用结果，并写入个人记录。
- DeepSeek 公开问答通过：外部身份 `POST /ask` 使用 `deepseek-v4-flash` 返回 `mode=generate`，答案包含真实公开知识库引用；`GET /app/records` 随后返回该 requester 的 1 条 Web 问答记录和引用统计。
- Web/飞书身份映射通过：`POST /app/profile/bind-feishu` 将浏览器 requester 绑定到飞书 open_id 后默认保持外部用户，`GET /app/profile` 显示公开知识范围，`GET /app/records` 可按浏览器 requester + 飞书 open_id 合并读取个人历史。
- 内部敏感访问通过：内部身份检索 `AI` 时可返回 `sensitive/内部折扣规则.md`，证明敏感分区只对内部身份开放。
- 敏感云端策略复验通过：管理员策略 `allow_sensitive_cloud=false` 时，内部身份命中敏感引用后问答返回 `mode=excerpt_only` 和本地原文，未把敏感内容交给 DeepSeek 生成。
- 外部降级边界通过：外部身份查询“内部折扣规则 八五折”时，检索结果和 DeepSeek 问答引用均只包含 `public/...`，未返回 `sensitive/...`，回答明确未找到内部折扣规则。

## 2026-07-16 普通用户端快捷入口阶段

- `/app/shortcuts` 已替换占位页，不新建平行数据表，直接复用 `GET /app/records` 的个人记录生成高频入口。
- 快捷入口仅按当前浏览器 requester 与绑定的飞书 open_id 聚合，不展示全局热门问题或管理员统计。
- 高频入口按同一查询词与类型聚合，展示使用次数、引用总数和最近使用；最近使用列表保留个人最新记录。
- 原文查询与知识问答页面已支持 `?q=` 参数，快捷入口点击后会把原查询词带入 `/app/search` 或 `/app/chat`，由用户确认后再执行查询/问答。
- 空状态提供“去查询原文”和“去知识问答”入口；已合并身份卡显示当前身份、记录来源和可访问范围。
- 真实 API 检查通过：`GET /app/records?requester_id=web-acceptance-public&limit=3` 返回 1 条个人 Web 问答记录、5 条引用统计，可用于生成快捷入口。
- 自动化回归为 12 项记录、profile 和 ask 测试通过；前端 TypeScript 与 Vite 生产构建通过；`/app/shortcuts` 路由由 Vite 正常返回中文 HTML。
- 真实浏览器验收通过：`/app/shortcuts` 在当前测试身份下显示外部用户、Web/飞书合并记录来源、1 个“退款期限”高频入口和最近使用记录。
- 快捷入口跳转验收通过：点击高频入口进入 `/app/search?q=退款期限`，原文查询输入框已预填“退款期限”，不会自动发起模型或检索请求。
- 移动端验收通过：390 × 844 下 `/app/shortcuts` 的 `scrollWidth` 与 `clientWidth` 均为 390px，无页面级横向溢出；控制台无 error。
- 提交前复核通过：前端 TypeScript 与 Vite 生产构建通过；后端记录、profile 和 ask 相关测试 12 项通过。

## 2026-07-16 普通用户端最终收口审计

- `/app/history` 已有当前证据：`GET /app/records` 返回个人记录、原文查询数、知识问答数、网页/飞书来源数和引用统计；页面仅展示当前身份的个人历史，不展示全局记录。
- `/app/profile` 已有当前证据：`GET /app/profile` 可返回浏览器 requester、飞书 open_id、外部/内部角色、可访问范围和个人记录统计；飞书绑定默认外部用户，管理员授权才可成为内部用户。
- Web/飞书身份映射已有当前证据：同一请求可同时传入浏览器 requester 与飞书 open_id，`/app/records` 合并返回个人历史，`/app/shortcuts` 也复用同一合并规则生成个人高频入口。
- DeepSeek 真实问答已有当前证据：当前配置 `active_provider=deepseek`、`api_key_configured=true`、模型 `deepseek-v4-flash`；真实 `POST /ask` 返回 `mode=generate` 和公开知识引用。
- 敏感云端策略已有当前证据：当前配置 `allow_sensitive_cloud=false`；内部身份命中 `sensitive/内部折扣规则.md` 时，即使请求体携带 `allow_sensitive_cloud=true`，服务端仍返回 `mode=excerpt_only` 和本地原文。
- 向量库当前运行时证据已复查：业务库 `private_knowledge`、公开向量库 `private_knowledge_public`、敏感向量库 `private_knowledge_sensitive` 均存在；公开向量库当前为 `documents=2155`、`chunks=2154`、`embeddings=6668`，敏感向量库当前为 `documents=3`、`chunks=3`、`embeddings=7`。
- 业务元数据当前运行时证据已复查：`private_knowledge` 中 `knowledge_sources=16`、`document_chunks=1820`；扫描后的业务元数据与 RAGLite/pgvector 向量索引均已落库。
- 仍保留的外部限制：飞书群聊 `@机器人` 因当前测试账号没有企业内部群权限暂缓，不阻塞本目标要求的普通用户端 Web/飞书身份合并、私聊记录和用户侧闭环。

## 下一步

普通用户端闭环已完成当前目标范围内的收口审计；下一步进入 `/app/documents` 文档中心，展示当前用户可访问的公开/敏感文档清单、扫描状态和引用入口。
