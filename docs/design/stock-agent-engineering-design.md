# 股票与指数信息推送 Agent 工程设计方案

版本：v0.1  
日期：2026-06-24  
来源 PRD：`docs/prd/stock-info-agent-prd.md`  
状态：Draft  

## 1. 设计目标

第一版本构建一个单用户、本地部署的 A 股股票与指数信息推送 Agent。系统需要通过本地 Web 界面完成配置和信息展示，并将重要异动、早报、复盘摘要通过 Server酱 Turbo 推送到手机微信。

工程目标：

- 支持 A 股股票和 A 股相关指数的关注列表管理
- 支持每日早报、盘中异动预警、收盘复盘
- 支持 Server酱 Turbo 作为默认主推送通道，企业微信群机器人 Webhook 作为可选备用通道
- 支持本地 Web 配置和信息展示
- 支持结构化证据、推送历史、去重键和端到端延迟记录
- 盘中重要异动在数据源可用后 2 分钟内完成推送，P95 延迟可观测

非目标：

- 不做自动交易
- 不做多用户、团队权限、云端 SaaS
- 不做港股、美股和海外市场
- 不承诺高频交易级实时行情或毫秒级延迟
- 不使用个人微信逆向协议或非官方登录态

## 2. 推荐技术架构

第一版本推荐采用本地单体架构，内部按模块分层。这样部署简单、调试直接，同时保留未来拆分 Worker、队列和前端的边界。

```text
Browser
  -> Web UI
    -> FastAPI HTTP API
      -> Config Service
      -> Scheduler Service
      -> Data Collector
      -> Signal Engine
      -> LLM Analyst
      -> Guardrail
      -> Push Service
      -> History Service
      -> SQLite
```

推荐技术选型：

- 后端：Python + FastAPI
- 本地存储：SQLite，预留后续切换 MySQL
- ORM/迁移：SQLModel 或 SQLAlchemy + Alembic
- 调度：APScheduler
- 队列：第一版本使用 SQLite-backed job 表或进程内优先级队列；后续可替换为 Redis/RQ
- Web UI：FastAPI 静态页面 + Jinja/HTMX，或 Vite/React。第一版本优先 Jinja/HTMX，减少前端工程复杂度
- HTTP 客户端：httpx
- LLM 接入：通过内部 `LLMProvider` 抽象封装，避免业务逻辑绑定具体模型供应商
- 配置：`.env` + 数据库配置表；敏感字段在日志中脱敏

存储层约束：

- 后端通过 Repository 或 Store 接口访问数据库，业务服务不直接依赖 SQLite
- 数据库连接统一使用 `DATABASE_URL` 配置，第一版本默认 `sqlite:///stock_agent.db`
- 表结构通过 Alembic 迁移管理，迁移脚本需要避免 SQLite 专有语法
- 字段类型优先使用 SQLite 和 MySQL 都兼容的基础类型
- JSON 内容在应用层序列化和反序列化，不依赖数据库 JSON 专有查询能力
- 后续切换 MySQL 时，目标是替换连接串、执行迁移和数据导入，不重写核心业务模块

## 3. 模块设计

### 3.1 Web UI

职责：

- 管理关注标的：添加、删除、启停 A 股股票和指数
- 配置提醒：早报时间、收盘复盘时间、盘中预警开关、冷却时间
- 配置通道：Server酱 Turbo SendKey、可选企业微信群机器人 Webhook
- 展示信息：最近推送、盘中异动、证据来源、推送延迟、系统状态

边界：

- Web UI 不直接采集数据、不生成摘要、不发送推送
- Web UI 只通过后端 API 读写配置和查询结果

### 3.2 Config Service

职责：

- 维护单用户本地配置
- 校验股票/指数代码格式
- 校验推送通道配置是否完整
- 为 Scheduler 和 Worker 提供运行配置快照

关键配置：

- 关注标的列表
- 推送通道
- 早报/复盘时间
- 盘中预警开关
- 全局和单标的冷却时间
- 数据源配置
- LLM 配置

### 3.3 Scheduler Service

职责：

- 按 A 股交易日和交易时段创建任务
- 创建每日早报任务
- 创建盘中轮询和异动检测任务
- 创建收盘复盘任务
- 将任务写入 job 表或优先级队列

调度原则：

- 盘中异动任务优先级最高
- 早报和收盘复盘为定时批任务
- 数据源不可用时记录失败并重试，不生成无依据摘要

### 3.4 Data Collector

职责：

- 从数据源采集行情、公告、新闻、财务指标、指数成分信息
- 标准化成内部 `EvidenceItem`
- 记录来源、抓取时间、数据时间和原始引用

数据源策略：

- 第一版本数据源仍是开放问题，工程上先定义 `MarketDataProvider`、`NewsProvider`、`AnnouncementProvider` 接口
- 如果数据源支持实时订阅或 WebSocket，优先使用订阅
- 如果数据源只支持 HTTP 查询，则在交易时段对重点标的短轮询

### 3.5 Signal Engine

职责：

- 用确定性规则识别异动信号
- 输出结构化 `SignalEvent`
- 生成去重键，避免重复推送

第一版本规则：

- 日内涨跌幅超过阈值
- 成交量超过近 20 日均量阈值
- 突破近 20 日高点或低点
- 发布财报或重大公告
- 负面或正面新闻数量显著增加
- 指数大幅波动、突破关键区间或代表性成分股集中异动

### 3.6 LLM Analyst

职责：

- 只基于结构化证据生成摘要
- 生成早报、异动摘要和收盘复盘
- 输出事实、推断、风险提示和后续观察指标

实时性约束：

- 盘中预警摘要生成设置 30 秒超时
- 超时后降级为结构化事实摘要
- LLM 不直接访问未校验外部数据

### 3.7 Guardrail

职责：

- 校验数字、时间、价格、百分比是否能回溯到证据
- 拦截买入、卖出、稳赚、必涨等投资建议式表述
- 检查风险提示、证据来源和重复事件
- 校验失败时返回降级策略

### 3.8 Push Service

职责：

- 默认通过 Server酱 Turbo 推送手机微信
- 可选通过企业微信群机器人 Webhook 作为备用通道
- 管理重试、超时、失败记录和降级通道

推送策略：

- 手机微信只推送高信号密度摘要和关键证据
- 完整证据和历史记录在 Web UI 查看
- 主通道失败后按配置切换备用通道

### 3.9 History Service

职责：

- 记录推送历史
- 记录事件去重键
- 记录采集、触发、入队、发送完成时间
- 提供 Web UI 查询接口
- 计算 P50、P95、P99 推送延迟

## 4. 核心数据模型

第一版本使用 SQLite 保存以下表。表设计需要保持 MySQL 可迁移性：主键、时间字段、状态枚举、文本字段和 JSON 字段都通过 ORM 定义；业务代码只依赖领域模型和 Repository 接口，不直接依赖数据库方言。

### 4.1 watch_targets

关注标的表。

```text
id
symbol
name
market
target_type
enabled
cooldown_minutes
created_at
updated_at
```

### 4.2 jobs

任务表。

```text
id
job_type
priority
status
payload_json
scheduled_at
started_at
finished_at
retry_count
error_message
created_at
updated_at
```

### 4.3 evidence_items

证据表。

```text
id
symbol
target_type
evidence_type
source
source_url
data_timestamp
collected_at
payload_json
created_at
```

### 4.4 signal_events

信号事件表。

```text
id
event_id
symbol
target_type
signal_type
severity
dedupe_key
triggered_at
evidence_ids_json
status
created_at
updated_at
```

### 4.5 push_records

推送记录表。

```text
id
push_id
event_id
symbol
target_type
channel
status
dedupe_key
content
first_collected_at
signal_triggered_at
queued_at
sent_at
delivery_latency_ms
fallback_from_channel
error_message
created_at
```

### 4.6 app_settings

本地单用户配置表。

```text
key
value_json
is_secret
updated_at
```

敏感配置如 Server酱 SendKey 可先本地保存，日志必须脱敏。后续可增加 OS keychain 或本地加密。

### 4.7 数据访问层

工程上需要为每类核心数据定义 Repository 或 Store：

```text
WatchTargetRepository
JobRepository
EvidenceRepository
SignalEventRepository
PushRecordRepository
SettingsRepository
```

Repository 负责封装查询、分页、写入、状态流转和事务边界。Service 层只调用 Repository 方法，不直接写 SQL。这样第一版本可以使用 SQLite，本地部署稳定后再迁移到 MySQL。

MySQL 预留要求：

- 所有表都使用显式主键和索引
- `symbol`、`event_id`、`push_id`、`dedupe_key` 等查询字段需要建立索引
- 时间字段统一使用带时区语义的 UTC 或 Asia/Shanghai 标准，避免数据库时区差异
- JSON 字段只做整体读写，不在第一版本依赖数据库 JSON 查询
- 分页查询使用 ORM 的通用 limit/offset 或游标模式，不使用 SQLite 专有语法

## 5. 关键数据流

### 5.1 盘中异动预警

```text
Scheduler
  -> create intraday_scan job
  -> Data Collector fetches latest market/news data
  -> Signal Engine detects event
  -> History Service checks dedupe and cooldown
  -> LLM Analyst generates short summary
  -> Guardrail validates facts and wording
  -> Push Service sends via Server酱 Turbo
  -> History Service stores record
  -> Web UI displays event and push result
```

降级路径：

- LLM 超时：发送结构化事实摘要
- Guardrail 失败：只发送事实和证据，不发送推断
- Server酱失败：记录失败；如果已配置企业微信群机器人，则切换备用通道

### 5.2 每日早报

```text
Scheduler
  -> create morning_report job
  -> Data Collector fetches overnight data
  -> Signal Engine ranks noteworthy targets
  -> LLM Analyst generates report
  -> Guardrail validates report
  -> Push Service sends concise version
  -> Web UI stores full version
```

### 5.3 收盘复盘

```text
Scheduler
  -> create closing_review job
  -> Data Collector fetches day summary
  -> Signal Engine summarizes important events
  -> LLM Analyst generates review
  -> Guardrail validates review
  -> Push Service sends concise version
  -> Web UI stores full version
```

## 6. HTTP API 草案

### 6.1 配置

```text
GET    /api/settings
PUT    /api/settings
POST   /api/channels/server-chan/test
POST   /api/channels/wecom-webhook/test
```

### 6.2 关注标的

```text
GET    /api/watch-targets
POST   /api/watch-targets
PATCH  /api/watch-targets/{id}
DELETE /api/watch-targets/{id}
```

### 6.3 事件与推送

```text
GET    /api/events
GET    /api/events/{event_id}
GET    /api/push-records
GET    /api/push-records/{push_id}
```

### 6.4 系统状态

```text
GET    /api/status
GET    /api/jobs
POST   /api/jobs/{id}/retry
POST   /api/jobs/run-morning-report
POST   /api/jobs/run-closing-review
POST   /api/jobs/run-intraday-scan
```

手动触发接口用于本地调试和验收，不代表生产调度方式。

## 7. 实时性设计

实时性目标是业务实时提醒。端到端计时从数据源数据可用或首次采集成功开始，到推送服务提交成功结束。

延迟预算：

- 数据采集轮询间隔：15-60 秒
- 信号识别和去重：10 秒内
- 摘要生成和 Guardrail：30 秒内
- 推送提交：10 秒内
- 盘中重要异动端到端 P95：2 分钟内

保障措施：

- 盘中扫描使用高优先级任务
- 扫描任务只处理启用标的
- 去重和冷却在 LLM 前执行，减少无效生成
- LLM 超时后降级为事实摘要
- 推送通道设置超时和有限重试
- 每条推送记录延迟字段，Web UI 展示最近 P95

## 8. 开发迭代计划

### Iteration 1：本地骨架、配置和每日早报

目标：打通从本地 Web 配置到早报生成和手机微信推送的最短闭环。

范围：

- 项目脚手架
- FastAPI 服务
- SQLite 数据模型、Repository 层和迁移脚本
- `DATABASE_URL` 配置，预留后续 MySQL 连接串
- 本地 Web 配置页
- 关注标的 CRUD
- Server酱 Turbo 配置和测试发送
- A 股交易日和早报调度基础能力
- 数据源 Provider 接口和一个可替换的 Mock Provider
- 每日早报基础生成
- 推送历史列表

验收：

- 可以在 Web UI 添加至少 5 个 A 股关注标的
- 可以配置 Server酱 SendKey 并测试发送
- 可以手动触发早报任务
- 早报内容写入历史，并通过 Server酱发送到手机微信
- JSON/配置/密钥日志脱敏规则可验证
- 业务服务不直接依赖 SQLite，Repository 层可通过测试替换存储实现

### Iteration 2：真实 A 股数据接入和盘中异动预警

目标：接入真实或准真实 A 股数据源，建立确定性规则预警和实时推送链路。

范围：

- 接入选定 A 股行情数据源
- 行情、成交量、指数数据标准化
- 盘中短轮询任务
- Signal Engine 规则实现
- 冷却时间和去重键
- 高优先级预警任务
- Web 异动事件列表
- 推送延迟字段采集

验收：

- 系统能识别至少 3 类异动信号
- 单个事件在冷却时间内不重复推送
- 异动事件在 Web UI 可查看
- 推送记录包含采集、触发、入队、发送完成时间
- 在 Mock 延迟测试下，P95 推送延迟统计可计算

### Iteration 3：LLM 摘要、Guardrail 和收盘复盘

目标：把结构化信号变成可读摘要，并保证事实可回溯、文案合规。

范围：

- LLMProvider 抽象
- 盘中异动短摘要模板
- 每日早报模板完善
- 收盘复盘生成
- Guardrail 事实校验和高风险措辞拦截
- LLM 超时降级为结构化事实摘要
- Web 详情页展示证据链、事实、推断、风险提示

验收：

- 摘要只引用结构化证据
- Guardrail 能拦截明显投资建议式文案
- LLM 超时时系统仍可推送事实摘要
- Web UI 能查看每条摘要的证据来源
- 收盘后可生成复盘并推送摘要

### Iteration 4：可靠性、可观测性和本地运行体验

目标：让单用户本地工具稳定运行、方便排障，并达到 PRD 的实时性和可运维要求。

范围：

- 任务失败重试
- 推送失败重试和备用通道
- 系统状态页
- P50、P95、P99 延迟统计
- 数据源失败率、推送成功率、Guardrail 拦截数量
- 本地启动脚本和配置模板
- 基础测试覆盖
- 数据库备份和日志轮转策略
- SQLite 到 MySQL 的迁移预案文档

验收：

- 数据源失败时不会生成无依据摘要
- Server酱失败时能记录失败原因；配置了企业微信备用通道时可降级
- 系统状态页可查看任务、数据源、LLM、Guardrail、推送通道状态
- 盘中重要异动 P95 延迟可从日志或 Web UI 追溯
- 本地启动步骤清晰，重启后历史记录不丢失
- 有明确的 MySQL 切换步骤，包括连接配置、迁移执行和数据导入边界

## 9. 测试策略

### 9.1 单元测试

- 代码格式和标的校验
- A 股交易时段判断
- Signal Engine 规则
- 去重键生成
- Guardrail 文案拦截
- Push Service 请求构造和失败处理

### 9.2 集成测试

- 配置保存到任务创建
- Mock 数据源到信号事件
- 信号事件到摘要生成
- 摘要到 Guardrail
- Guardrail 到推送历史

### 9.3 端到端测试

- 添加标的，手动触发早报，查看 Web 历史
- 模拟盘中异动，验证微信推送和 Web 展示
- 模拟 LLM 超时，验证事实摘要降级
- 模拟主通道失败，验证失败记录和备用通道

## 10. 主要风险与工程应对

### 10.1 A 股数据源不确定

风险：数据源权限、频率、字段质量和稳定性不确定。  
应对：先定义 Provider 接口和 Mock Provider；真实数据源作为可替换适配器接入。

### 10.2 本地任务与 Web 服务互相影响

风险：盘中扫描阻塞 Web 请求或导致响应变慢。  
应对：后台任务与 API 请求隔离；长任务只写 job 表，由 Worker 执行。

### 10.3 LLM 生成慢或不可用

风险：影响实时预警。  
应对：设置超时；预警链路优先生成结构化事实摘要；完整分析可稍后补齐。

### 10.4 推送通道不稳定

风险：Server酱或微信链路延迟、限流、失败。  
应对：记录通道失败率；设置超时和有限重试；支持企业微信群机器人备用通道。

### 10.5 本地密钥泄露

风险：SendKey、LLM Key、数据源 Key 出现在日志或仓库。  
应对：使用 `.env` 和本地配置表；日志脱敏；提供 `.env.example`，不提交真实密钥。

### 10.6 后续切换 MySQL 成本过高

风险：第一版本如果直接使用 SQLite 专有 SQL、文件路径假设或无迁移脚本，后续切换 MySQL 会牵动大量业务代码。  
应对：第一版本就引入 Repository/Store 抽象、`DATABASE_URL`、Alembic 迁移和数据库兼容字段类型；业务服务只依赖 Repository 接口。

## 11. 推荐目录结构

```text
stock_agent/
  app/
    main.py
    api/
    core/
    models/
    repositories/
    services/
    providers/
    workers/
    web/
    templates/
    static/
  tests/
  migrations/
  scripts/
docs/
  prd/
  design/
```

模块说明：

- `api/`：HTTP API 路由
- `core/`：配置、日志、时间、异常、依赖注入
- `models/`：数据库模型和领域对象
- `services/`：业务服务
- `providers/`：数据源、LLM、推送通道适配器
- `workers/`：任务调度和后台执行
- `web/`、`templates/`、`static/`：本地 Web UI
- `repositories/`：数据库访问封装，隔离 SQLite 和后续 MySQL 差异

## 12. 后续决策点

仍需在实现前确认：

- A 股行情、公告、新闻和指数数据源
- LLM 供应商和模型
- 本地 Web UI 采用 Jinja/HTMX 还是 React/Vite
- 是否需要在第一版本加入企业微信群机器人备用通道，还是仅预留接口
- MySQL 切换时机和部署方式
