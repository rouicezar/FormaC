# CoreKnowledge Stitch 设计冻结清单

冻结日期：2026-07-15

本目录是正式前端开发的视觉参考源，不是可直接投产的前端代码。`screen.png` 用于还原视觉与布局，`code.html` 仅用于提取尺寸、颜色和组件结构；正式实现必须复用当前 React 工程、现有 API 与仓库模板能力。导出包中 3 张截图拉取失败，已删除伪图片；对应的 `admin/analytics`、`admin/retrieval-lab`、`admin/scan-detail` 仍保留完整 HTML 画板。

## 使用铁律

- 原文查询只检索和展示原始资料，不调用大模型。
- 知识问答先检索知识库，再由模型基于证据总结或汇总，并展示引用。
- 系统只读取管理员授权的本地 `public/` 与 `sensitive/` 目录，不提供上传、删除、移动或修改源文件的入口。
- 匿名用户可使用公开知识；绑定飞书后默认仍是外部用户；只有管理员明确授权后才成为内部用户。
- 外部与匿名用户只能访问公开知识，内部用户可访问公开与敏感知识。身份识别失败一律降级为外部用户。
- 敏感内容不允许发送云端时，云端模型不得收到敏感片段，界面只返回原文检索结果；配置的本地模型可以总结敏感内容。
- 飞书仅使用纯文本交互，不设计菜单和消息卡片。
- 所有正式界面、状态、提示和无障碍文案使用简体中文。

## 正式画板映射

| 目录 | 正式路由 | 页面或状态 |
| --- | --- | --- |
| `app/home` | `/app/home` | 用户首页、动态身份与可见范围 |
| `app/search-default` | `/app/search` | 原文查询默认态 |
| `app/search-results` | `/app/search` | 原文查询结果态 |
| `app/search-empty` | `/app/search` | 原文查询无结果态 |
| `app/chat-answer` | `/app/chat` | 有证据的问答与引用 |
| `app/chat-evidence-insufficient` | `/app/chat` | 证据不足拒答态 |
| `app/chat-sensitive-cloud-blocked` | `/app/chat` | 敏感内容禁止发云端时的原文降级态 |
| `app/shortcuts` | `/app/shortcuts` | 用户快捷入口 |
| `app/history` | `/app/history` | 个人查询与问答历史 |
| `app/history-sensitive-blocked` | `/app/history` | 身份降级后的敏感历史受阻态 |
| `app/documents` | `/app/documents` | 授权文档只读浏览 |
| `app/bind-feishu` | `/app/bind-feishu` | 飞书绑定与匿名历史合并确认 |
| `app/bind-feishu-success` | `/app/bind-feishu` | 绑定成功、默认外部身份提示 |
| `app/profile` | `/app/profile` | 个人中心 |
| `admin/login` | `/admin/login` | 超级管理员登录 |
| `admin/dashboard` | `/admin/dashboard` | 管理首页，查询与问答指标分列 |
| `admin/knowledge` | `/admin/knowledge` | 本地路径和扫描管理 |
| `admin/scan-detail` | `/admin/knowledge/scan-detail` | 扫描任务详情 |
| `admin/scan-error` | `/admin/knowledge/scan-detail` | 路径丢失或无权限诊断态 |
| `admin/models` | `/admin/models` | 云端与本地模型配置 |
| `admin/models-sensitive-confirm` | `/admin/models` | 敏感内容发云端二次确认 |
| `admin/users` | `/admin/users` | 用户身份授权与降级 |
| `admin/records` | `/admin/records` | 全局查询与问答记录 |
| `admin/analytics` | `/admin/analytics` | 数据分析 |
| `admin/shortcuts` | `/admin/shortcuts` | 快捷入口管理 |
| `admin/feishu` | `/admin/feishu` | 飞书接入配置 |
| `admin/audit` | `/admin/audit` | 审计日志 |
| `admin/retrieval-lab` | `/admin/retrieval-lab` | 检索链路调试 |

## 开发时必须修正的 Stitch 残留

- 删除所有 `Add New Source`、`New Workspace`、上传文件及类似入口。
- 统一产品名为 `CoreKnowledge`，统一中文用户端与管理端导航，不照搬画板中的英文侧栏。
- 首页称呼和身份标签必须来自真实会话，不能固定显示“系统管理员”或“内部员工”。
- 飞书绑定成功后必须显示“外部用户”；管理员授权前不得显示内部身份。
- 用户管理不是“注册审核”：用户绑定即成为外部用户，管理员操作是“授权为内部用户”或“降级为外部用户”。
- 模型页不得假定特定显卡或固定本地模型；展示实际提供商、连接状态和设备信息。
- 文档中心只有只读列表与预览，不允许上传、编辑、移动和删除源文件。
- 飞书页删除卡片、菜单和按钮协议，只保留纯文本命令：`查询：问题`、`问答：问题`、`历史`、`帮助`；无前缀文本默认按问答处理。

## 已删除画板

共删除 14 个：`403`、`_1`、`_2`、`_3`、`_4`、`_5`、`_6`、`_11`、`_16`、`_18`、`_19`、`_24`、`_27`、`app_documents_1`。

删除原因包括：已有更完整的同路由版本、英文旧模板占比过高、视觉质量明显较低、重复状态，或包含上传等违反产品规则的交互。通用 403 状态改由正式前端的全局异常组件统一实现，不单独保留旧画板。

## 视觉规范

全局色彩、字体、间距和圆角以 `design-system/DESIGN.md` 为视觉基准；其中英文说明文字不作为产品文案。正式页面使用温和米白背景、低饱和墨绿主色、深灰绿正文，禁止纯黑大面积背景、荧光色、强渐变和发光效果。

通用加载、成功、失败、404、403、表单校验和键盘焦点状态见 `component-states.md`。这些状态必须结合当前操作给出准确动作，不得机械显示“新建”或“申请提升权限”。
