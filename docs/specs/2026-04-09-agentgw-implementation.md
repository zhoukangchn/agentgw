# agentgw 实现文档

日期：2026-04-09

本文档基于 [agentgw channel-centric 规格说明](/home/kangz/project/agentgw/docs/specs/2026-04-09-agentgw-channel-centric-spec.md)，描述第一版实现应如何落地，包括模块划分、数据表、接口范围、阶段顺序与关键约束。

## 1. 实现目标

第一版实现目标不是覆盖所有企业渠道能力，而是优先跑通三类标准业务 channel：

1. `feishu_ingress`
   飞书只采集，发送到 agent，不做出站回复
2. `feishu_to_welink_group`
   飞书采集，发送到 agent，agent 最终结果发到 WeLink 群
3. `welink_dm_twoway`
   WeLink 私聊进入 agent，agent 最终结果回同一个 WeLink 私聊会话

第一版必须保证：

- `channel` 是业务路由中心
- `agent endpoint` 独立于 `channel`
- 同时支持 `ws_rpc` 和 `sdk_session`
- ingress / agent / egress 全链路都有消息记录

## 2. 实现边界

第一版实现包含：

- Channel 配置加载与匹配
- Agent endpoint 配置加载与选择
- Conversation 映射
- Message 记录
- `ws_rpc` agent transport
- `sdk_session` agent transport
- WeLink 群出站
- WeLink 私聊出站
- 飞书 ingress adapter
- WeLink 私聊 ingress adapter
- 供联调使用的 HTTP 管理接口

第一版实现不包含：

- 企业微信接入
- 完整权限模型
- 多租户隔离策略
- 高可用部署
- 复杂重试编排
- 完整监控告警体系

## 3. 模块划分

建议实现目录：

```text
src/agentgw/
  domain/
    channel/
    agent/
    conversation/
    message/
  application/
    routing/
    orchestration/
  adapters/
    ingress/
      feishu/
      welink_dm/
    egress/
      welink_group/
      welink_dm/
    agent/
      ws_rpc/
      sdk_session/
  infrastructure/
    persistence/
    config/
  interfaces/
    http/
```

各层职责如下：

### 3.1 domain

负责稳定业务模型，不依赖外部 SDK。

核心对象：

- `Channel`
- `AgentEndpoint`
- `Conversation`
- `Message`

### 3.2 application.routing

负责将入站事件解析到具体业务 channel。

核心职责：

- 根据 `channel_id` 或 routing key 查找 channel
- 校验 source account 是否匹配
- 解析 channel 对应的 agent endpoint

### 3.3 application.orchestration

负责组织整个运行时流程。

核心职责：

- 接收入站请求
- 创建或查找 conversation
- 写入 inbound message
- 调用 agent transport
- 写入 agent message
- 调用 egress adapter
- 写入 egress message

### 3.4 adapters.ingress

负责把平台消息转换成统一入站事件。

第一阶段：

- `feishu`
- `welink_dm`

### 3.5 adapters.agent

负责把统一运行时请求发送给 agent。

第一阶段：

- `ws_rpc`
- `sdk_session`

### 3.6 adapters.egress

负责把 agent 输出发到目标渠道。

第一阶段：

- `welink_group`
- `welink_dm`
- `none`

### 3.7 infrastructure.persistence

负责配置和业务记录持久化。

第一阶段建议直接使用 SQLite，便于联调。

## 4. 数据模型

## 4.1 channels

用于存储业务 channel 定义。

建议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `channel_id` | text pk | 业务 channel 唯一标识 |
| `name` | text | channel 名称 |
| `ingress_type` | text | `feishu` / `welink_dm` |
| `ingress_account_id` | text | 源账号 |
| `agent_endpoint_id` | text | 关联 endpoint |
| `egress_type` | text | `none` / `welink_group` / `welink_dm` |
| `egress_target_id` | text null | 固定出站目标 |
| `use_source_conversation` | bool | 是否复用源会话 |
| `mode` | text | `ingress_only` / `oneway` / `twoway` |
| `enabled` | bool | 是否启用 |
| `config_json` | text null | 扩展配置 |

## 4.2 agent_endpoints

用于存储 agent 连接配置。

建议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `endpoint_id` | text pk | endpoint 唯一标识 |
| `name` | text | endpoint 名称 |
| `transport` | text | `ws_rpc` / `sdk_session` |
| `url` | text | agent 地址 |
| `timeout_seconds` | int | 超时秒数 |
| `sdk_module` | text null | SDK 模块名 |
| `sdk_client_class` | text null | client 类名 |
| `sdk_event_enum` | text null | event enum 名称 |
| `enabled` | bool | 是否启用 |
| `config_json` | text null | 扩展配置 |

## 4.3 conversations

用于存储源会话到内部会话的映射。

建议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `conversation_id` | text pk | 内部会话 id |
| `channel_id` | text | 所属业务 channel |
| `source_conversation_id` | text | 源端会话 id |
| `source_user_id` | text | 源端用户 id |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

唯一索引建议：

- `(channel_id, source_conversation_id)`

## 4.4 messages

用于存储全链路消息记录。

建议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `message_id` | text pk | 消息 id |
| `channel_id` | text | 所属业务 channel |
| `conversation_id` | text | 内部会话 id |
| `sender_id` | text | 发送者 |
| `direction` | text | `inbound` / `agent` / `egress` |
| `content` | text | 文本内容 |
| `raw_payload_json` | text null | 原始负载 |
| `created_at` | datetime | 创建时间 |

## 5. 接口设计

第一阶段只实现管理和联调接口，不把它当成生产 ingress 标准。

建议接口：

### 5.1 `GET /healthz`

作用：

- 健康检查

### 5.2 `GET /channels`

作用：

- 查看当前 channel 配置

### 5.3 `GET /agent-endpoints`

作用：

- 查看当前 endpoint 配置

### 5.4 `POST /ingress/events`

作用：

- 手工提交一个统一入站事件
- 用于本地联调和端到端验证

请求体建议：

```json
{
  "channel_id": "feishu_to_welink_group",
  "source_account_id": "acc-feishu-default",
  "source_conversation_id": "feishu-chat-1",
  "sender_id": "user-1",
  "content": "hello"
}
```

### 5.5 `GET /messages`

作用：

- 查看当前已经记录的 inbound / agent / egress 消息

### 5.6 `GET /egress/welink`

作用：

- 查看 WeLink mock 出站结果

## 6. 关键时序

### 6.1 飞书转 WeLink 群

```text
Feishu -> ingress adapter -> channel router
       -> conversation resolver -> message store(inbound)
       -> ws_rpc transport -> agent
       -> message store(agent)
       -> welink_group egress
       -> message store(egress)
```

### 6.2 WeLink 私聊双向

```text
WeLink DM -> ingress adapter -> channel router
          -> conversation resolver -> message store(inbound)
          -> sdk_session transport -> agent session
          -> collect normalized events
          -> message store(agent)
          -> welink_dm egress
          -> message store(egress)
```

## 7. 关键实现约束

1. 不允许用 `message.channel_type` 兼做来源、路由和出站目标。
2. `channel` 与 `agent endpoint` 必须分表。
3. `ws_rpc` 与 `sdk_session` 必须共用统一的编排入口。
4. WeLink 私聊双向必须依赖 `conversation` 映射，而不是临时字符串拼接。
5. 所有出站都要有消息记录。
6. 任何平台 adapter 都不能直接决定 agent transport。

## 8. 阶段计划

### 阶段 1：最小闭环

目标：

- SQLite 持久化
- 内置三条 canonical channels
- 跑通 `ws_rpc`
- 跑通 `sdk_session`
- 跑通 WeLink mock egress
- 跑通手工联调接口

交付标准：

- 能手工提交飞书消息并发到 WeLink 群
- 能手工提交 WeLink 私聊消息并回到原会话

### 阶段 2：真实渠道接入

目标：

- 接入飞书真实 ingress
- 接入 WeLink 私聊真实 ingress / egress
- 补齐基础鉴权和错误处理

交付标准：

- 能从真实飞书会话接收入站消息
- 能向真实 WeLink 群和私聊发送消息

### 阶段 3：生产化增强

目标：

- 配置管理
- 观测
- 重试与补偿
- 更明确的部署方式

交付标准：

- channel 与 endpoint 可配置化管理
- 有完整链路日志与关键指标

## 9. 开发顺序建议

推荐按以下顺序实现：

1. 持久化模型与表结构
2. `ChannelRepository` 与 `AgentEndpointRepository`
3. `ConversationRepository` 与 `MessageRepository`
4. `ChannelRouter`
5. `RuntimeOrchestrator`
6. `ws_rpc` transport
7. `sdk_session` transport
8. `welink_group` egress
9. `welink_dm` egress
10. HTTP 管理接口
11. 飞书 ingress adapter
12. WeLink 私聊 ingress adapter

## 10. 验收清单

第一版完成时，至少应满足：

- 飞书只采集场景可跑通
- 飞书转 WeLink 群场景可跑通
- WeLink 私聊双向场景可跑通
- `ws_rpc` 与 `sdk_session` 都可被同一编排入口使用
- 数据库中可追踪每一条 inbound、agent、egress 消息
- channel 与 endpoint 可独立配置
