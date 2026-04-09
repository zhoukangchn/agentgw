# agentgw channel-centric 规格说明

日期：2026-04-09

## 1. 目标

`agentgw` 是一个以业务 `channel` 为核心的 agent gateway，用于将企业消息渠道中的入站消息路由到 agent 运行时，并按业务规则决定是否将 agent 输出转发到其他出站渠道。

当前仓库只记录目标产品模型，不包含参考实现。

## 2. 设计原则

1. `channel` 是业务路由单元，不是平台 SDK client。
2. 入站与出站解耦。
3. agent 连接方式与业务路由解耦。
4. 会话能力必须显式建模，不能由平台类型隐式推导。
5. “飞书只采集”和“WeLink 私聊双向”都属于一等场景。

## 3. 核心概念

### 3.1 Channel

`channel` 表示一条完整的业务路由规则。

必需属性：

- `channel_id`
- `name`
- `ingress`
- `agent`
- `egress`
- `mode`
- `enabled`

### 3.2 Ingress

`ingress` 定义消息从哪里进入网关。

第一阶段支持的入站类型：

- `feishu`
- `welink_dm`

入站属性：

- `type`
- `account_id`
- 可选的源端专属配置

### 3.3 Agent endpoint

`agent endpoint` 定义 `agentgw` 如何连接 agent 运行时。

第一阶段支持的连接类型：

- `ws_rpc`
- `sdk_session`

endpoint 属性：

- `endpoint_id`
- `name`
- `transport`
- `url`
- `timeout_seconds`
- 可选的 SDK 配置

### 3.4 Egress

`egress` 定义 agent 输出发往哪里。

第一阶段支持的出站类型：

- `none`
- `welink_group`
- `welink_dm`

出站属性：

- `type`
- 可选的 `target_id`
- 可选的 `use_source_conversation`

### 3.5 Mode

`mode` 定义 channel 的交互形态。

第一阶段支持的模式：

- `ingress_only`
- `oneway`
- `twoway`

语义如下：

- `ingress_only`：消息进入 agent，但 agent 输出不向外发送
- `oneway`：消息进入 agent，agent 最终输出发送到固定出站目标
- `twoway`：消息进入 agent，agent 输出回到对应的实时会话

### 3.6 Conversation

`conversation` 用于将源端会话身份映射到 gateway 内部运行时会话。

属性：

- `conversation_id`
- `channel_id`
- `source_conversation_id`
- `source_user_id`

### 3.7 Message

`message` 是网关内部的不可变消息事件记录。

属性：

- `message_id`
- `channel_id`
- `conversation_id`
- `sender_id`
- `direction`
- `content`
- `created_at`

方向类型：

- `inbound`
- `agent`
- `egress`

## 4. 标准业务 Channel

### 4.1 飞书只采集

意图：

- 飞书仅承担入站采集
- agent 输出不回飞书

示例：

```yaml
channel_id: feishu_ingress
name: 飞书只采集
ingress:
  type: feishu
  account_id: acc-feishu-default
agent:
  endpoint_id: agent_ws_default
egress:
  type: none
mode: ingress_only
enabled: true
```

### 4.2 飞书转 WeLink 群

意图：

- 飞书负责采集入站消息
- agent 最终输出转发到指定 WeLink 群

示例：

```yaml
channel_id: feishu_to_welink_group
name: 飞书转 WeLink 群
ingress:
  type: feishu
  account_id: acc-feishu-default
agent:
  endpoint_id: agent_ws_default
egress:
  type: welink_group
  target_id: welink-group-demo
mode: oneway
enabled: true
```

### 4.3 WeLink 私聊双向

意图：

- WeLink 私聊既是入站也是出站
- agent 输出回到同一个私聊会话

示例：

```yaml
channel_id: welink_dm_twoway
name: WeLink 私聊双向
ingress:
  type: welink_dm
  account_id: acc-welink-default
agent:
  endpoint_id: agent_sdk_default
egress:
  type: welink_dm
  use_source_conversation: true
mode: twoway
enabled: true
```

## 5. Agent 连接协议

### 5.1 ws_rpc

`ws_rpc` 是建立在长连接 WebSocket 之上的请求-响应协议。

请求帧：

```json
{
  "type": "send_message",
  "request_id": "msg_123",
  "channel_id": "feishu_to_welink_group",
  "channel_mode": "oneway",
  "message_id": "msg_123",
  "conversation_id": "conv_123",
  "sender_id": "user_123",
  "content": "hello"
}
```

响应帧：

```json
{
  "type": "send_message_result",
  "request_id": "msg_123",
  "provider_message_id": "agent_msg_123",
  "content": "reply text"
}
```

### 5.2 sdk_session

`sdk_session` 是基于厂商 SDK client 的事件驱动会话协议。

预期的 client 形态：

- `async with client`
- `client.on(EventType.*)`
- `send_config(...)`
- `send_message(...)`
- `wait_until_done()`

预期的标准化事件类别：

- `agent_call`
- `tool_execution`
- `agent_text`
- `done`
- `error`

## 6. 运行时流程

### 6.1 通用流程

1. 从 ingress adapter 接收入站事件。
2. 解析目标业务 `channel`。
3. 校验 `source_account_id` 与 channel ingress 配置是否匹配。
4. 查找或创建 `conversation`。
5. 持久化入站消息记录。
6. 解析 agent endpoint。
7. 执行对应的 agent transport。
8. 持久化 agent 消息记录。
9. 如有需要，将输出投递到配置的 egress 目标。
10. 持久化 egress 消息记录。

### 6.2 飞书只采集

1. 接收飞书消息。
2. 路由到 `feishu_ingress`。
3. 发送到 agent endpoint。
4. 持久化 inbound 与 agent 记录。
5. 结束。

### 6.3 飞书转 WeLink 群

1. 接收飞书消息。
2. 路由到 `feishu_to_welink_group`。
3. 发送到 agent endpoint。
4. 取得 agent 最终输出。
5. 发送到指定 WeLink 群。
6. 持久化 inbound、agent 与 egress 记录。

### 6.4 WeLink 私聊双向

1. 接收 WeLink 私聊消息。
2. 路由到 `welink_dm_twoway`。
3. 查找或创建会话映射。
4. 使用 `sdk_session` 启动 agent 会话。
5. 收集会话事件。
6. 将 agent 最终输出回发到同一个 WeLink 私聊会话。
7. 持久化 inbound、agent 与 egress 记录。

## 7. 接口要求

第一阶段的 HTTP 管理面应支持：

- 查看 channel 列表
- 查看 agent endpoint 列表
- 手工提交 ingress 事件用于联调
- 查看记录下来的消息
- 查看 mock egress 输出

这个接口面只服务于开发与验证，不定义生产环境正式 ingress 协议。

## 8. 持久化要求

第一阶段生产可用的持久化层应支持：

- channel 配置存储
- agent endpoint 存储
- conversation 映射存储
- message 记录存储

建议表：

- `channels`
- `agent_endpoints`
- `conversations`
- `messages`

## 9. 非目标

本规格暂不定义：

- 飞书生产 API 集成细节
- WeLink 生产 API 集成细节
- 密钥管理细节
- 各 adapter 的完整重试语义
- 部署拓扑

## 10. 实施顺序

建议实现顺序：

1. channel 配置与 agent endpoint 持久化
2. 运行时编排与统一消息模型
3. `ws_rpc` agent transport
4. `sdk_session` agent transport
5. WeLink 群出站
6. WeLink 私聊出站
7. 飞书 ingress adapter
8. WeLink 私聊 ingress adapter
