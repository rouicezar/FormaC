# Private Knowledge Customer Service

面向内部员工和外部客户的私有知识库、自然语言问答与飞书客服一体化应用。

当前状态：需求与设计已确认，应用骨架已建立，业务实现尚未开始。

## 已确认范围

- 读取本地 `public/` 与 `sensitive/` 文件夹，不提供上传。
- 支持 PDF、DOCX、MD、TXT、XLSX 和 PPTX。
- 手动扫描与每隔一天自动增量扫描。
- 本地 Embedding、混合检索、重排和持久化。
- DeepSeek 等云端模型与 Ollama 等本地模型可插拔。
- 敏感知识默认禁止发送给云端模型。
- 飞书私聊、群聊问答及人工客服接管。
- 白名单用户为内部员工，其他用户均按外部客户处理。
- Web 管理后台、独立网页问答端和飞书交互端。
- 网页端支持飞书 OAuth 与本地账号密码。

## 文档

- [需求](docs/requirements.md)
- [设计](docs/design.md)
- [项目状态](docs/project-status.md)
- [实施计划](../../../docs/plans/2026-07-15-private-knowledge-customer-service.md)

## 计划结构

```text
backend/   FastAPI、知识索引、模型、客服和飞书适配
frontend/  React 管理后台与独立问答端
deploy/    本地部署、数据库和配置样例
docs/      应用需求、设计和进度
```

## 下一里程碑

完成阶段 1：数据库基础、授权目录校验、文件清单与增量扫描闭环。
