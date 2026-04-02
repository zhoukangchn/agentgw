# agentgw

`agentgw` 是一个面向渠道接入的 agent gateway。当前版本基于 FastAPI 和 DDD 风格分层实现，提供飞书、企业微信消息/联系人同步骨架，WebSocket agent 投递，以及内部 WeLink mock 群消息回写能力。

这个仓库当前更偏内部开发者接手和继续演进使用，不是面向外部用户的完整产品文档。

## 当前能力

- FastAPI 单进程服务入口
- 内嵌 scheduler，定时执行消息同步、联系人同步、delivery 处理
- `agentgw -> agent` 使用 WebSocket provider
- 企业微信消息增量同步骨架
- 飞书会话消息与部门用户同步骨架
- 内部 WeLink mock 群消息发送
- 管理接口：
  - `POST /admin/sync/messages`
  - `POST /admin/sync/contacts`
- SQLite 持久化默认配置

当前实现是第一版最小闭环，重点在统一分层、协议边界和可演进结构。飞书、企业微信 client 已按官方 API 结构落了骨架，但还没有扩展到完整生产级鉴权、限流和重试策略。

## 架构概览

项目按 `interfaces / application / domain / infrastructure` 分层：

- `src/agentgw/interfaces`
  - HTTP 控制器与请求 schema
- `src/agentgw/application`
  - 用例编排，例如消息同步、联系人同步、delivery 处理
- `src/agentgw/domain`
  - 领域实体、仓储接口、agent provider 协议
- `src/agentgw/infrastructure`
  - 渠道 client、WebSocket provider、SQLAlchemy 持久化、scheduler
- `src/agentgw/bootstrap`
  - 容器装配、FastAPI 应用入口

主链路：

1. scheduler 或管理接口触发消息/联系人同步
2. channel client 拉取飞书/企微数据
3. 数据写入消息表、联系人表、sync cursor
4. 为新消息创建 `Delivery`
5. delivery worker job 调用 WebSocket agent
6. 如果渠道是 WeLink，则把 agent 响应回写到群消息 mock client

## 目录

```text
src/agentgw/
  bootstrap/          应用装配与入口
  interfaces/         HTTP 接口层
  application/        用例服务
  domain/             领域对象与协议
  infrastructure/     外部系统实现
tests/
  integration/        接口集成测试
  unit/               单元测试
docs/superpowers/
  specs/              设计文档
  plans/              实现计划
```

## 快速开始

### 1. 准备环境

要求：

- Python 3.12+
- `uv`

安装依赖：

```bash
uv sync
```

### 2. 启动服务

```bash
uv run gateway
```

默认监听：

- `http://0.0.0.0:8000`

健康检查：

```bash
curl http://127.0.0.1:8000/healthz
```

### 3. 手动触发同步

触发消息同步：

```bash
curl -X POST http://127.0.0.1:8000/admin/sync/messages \
  -H 'Content-Type: application/json' \
  -d '{"account_id":"acc-1","channel_type":"wecom"}'
```

触发联系人同步：

```bash
curl -X POST http://127.0.0.1:8000/admin/sync/contacts \
  -H 'Content-Type: application/json' \
  -d '{"account_id":"acc-1","channel_type":"feishu"}'
```

如果 `channel_type` 不支持，接口会返回 `400`。

## 配置

当前使用 `pydantic-settings`，环境变量前缀为 `AGENTGW_`。

常用配置项：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `AGENTGW_APP_NAME` | `agentgw` | 应用名 |
| `AGENTGW_DATABASE_URL` | `sqlite+pysqlite:///./agentgw.db` | 数据库连接串 |
| `AGENTGW_AGENT_BASE_URL` | `ws://localhost:9000/ws` | agent WebSocket 地址 |
| `AGENTGW_SCHEDULER_ENABLED` | `true` | 是否启用内嵌 scheduler |
| `AGENTGW_MESSAGE_SYNC_INTERVAL_SECONDS` | `10` | 消息同步间隔 |
| `AGENTGW_CONTACT_SYNC_INTERVAL_SECONDS` | `300` | 联系人同步间隔 |
| `AGENTGW_MESSAGE_SYNC_TARGETS` | `""` | 消息同步目标，格式 `wecom:acc-1,feishu:acc-2` |
| `AGENTGW_CONTACT_SYNC_TARGETS` | `""` | 联系人同步目标，格式同上 |
| `AGENTGW_FEISHU_ACCESS_TOKEN` | 空 | 飞书 token |
| `AGENTGW_FEISHU_DEFAULT_CHAT_ID` | 空 | 飞书默认 chat id |
| `AGENTGW_FEISHU_DEPARTMENT_ID` | 空 | 飞书部门 id |
| `AGENTGW_WECOM_ACCESS_TOKEN` | 空 | 企业微信 token |
| `AGENTGW_WECOM_AUDIT_PROXY` | 空 | 企业微信会话内容存档代理参数 |
| `AGENTGW_WECOM_FOLLOW_USER_IDS` | 空 | 企业微信客户联系跟进人列表，逗号分隔 |

## 运行与测试

全量测试：

```bash
uv run pytest -v
```

启动验证：

```bash
timeout 5 uv run gateway
```

## 渠道实现说明

### 飞书

当前已按官方接口结构实现消息与联系人同步骨架，主要参考：

- 会话历史消息：`/open-apis/im/v1/messages`
- 部门直属用户：`/open-apis/contact/v3/users/find_by_department`

代码位置：

- [`src/agentgw/infrastructure/channels/feishu/client.py`](src/agentgw/infrastructure/channels/feishu/client.py)

### 企业微信

当前已按官方接口结构实现消息与外部联系人同步骨架，主要参考：

- 会话内容存档：`/cgi-bin/msgaudit/get_chatdata`
- 外部联系人列表：`/cgi-bin/externalcontact/list`
- 外部联系人详情：`/cgi-bin/externalcontact/get`

代码位置：

- [`src/agentgw/infrastructure/channels/wecom/client.py`](src/agentgw/infrastructure/channels/wecom/client.py)

### WeLink

当前只实现了 mock 群消息发送，用于打通 agent 返回后的内部回写分支：

- [`src/agentgw/infrastructure/channels/welink/client.py`](src/agentgw/infrastructure/channels/welink/client.py)

## 文档

设计和计划文档保存在：

- [`docs/superpowers/specs/2026-04-02-agentgw-channel-gateway-design.md`](docs/superpowers/specs/2026-04-02-agentgw-channel-gateway-design.md)
- [`docs/superpowers/plans/2026-04-02-agentgw-channel-gateway.md`](docs/superpowers/plans/2026-04-02-agentgw-channel-gateway.md)

## 后续规划

- 补齐生产级飞书/企微鉴权、分页和重试
- 引入更明确的 route rule / agent endpoint 持久化
- 将 scheduler 从单进程内嵌模式演进到独立 worker
- 增加 CI、镜像构建和部署说明
