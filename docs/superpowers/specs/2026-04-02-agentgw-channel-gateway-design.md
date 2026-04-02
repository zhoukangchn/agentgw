# Agent Gateway 渠道接入设计

## 背景

这个项目是一个基于 FastAPI 的 agent gateway，用于把飞书、企业微信等外部 IM 系统，以及内部 WeLink 接口型渠道接入到下游 agent。

第一版聚焦以下能力：

- 通过渠道 API 主动拉取最近消息，而不是依赖 webhook 推送
- 拉取联系人信息，并基于渠道侧标记识别内外部人员
- 将拉取到的消息转换为统一内部模型
- 将符合条件的消息路由到下游 agent
- 支持内部 WeLink mock 接口发送群消息
- 在实现上先采用定时同步模型，同时为后续演进到更事件化的执行方式保留空间

当前仓库还是空目录，因此这份文档定义初始架构和项目结构。

## 范围

### 本期范围

- FastAPI 单进程服务
- DDD 风格代码组织
- 飞书、企业微信的定时同步能力
- 内部 WeLink 群消息发送 mock 能力
- 联系人同步与消息同步
- 统一的消息接入模型
- 统一的 agent 投递模型
- 可插拔的 WebSocket agent provider
- 使用 `uv` 管理 Python 项目

### 非本期范围

- 第一版就拆成多进程独立部署
- 第一版就引入完整事件总线架构
- 复杂的会话生命周期管理
- 富编排工作流
- 多 agent 并行分发
- 人工审核流程

## 架构决策

第一版采用单个 FastAPI 服务进程，并在进程内嵌入 scheduler。

这个选择有意靠近 Spring Boot 风格的运行方式：

- 一个服务进程
- 同时提供 HTTP 接口
- 同时运行定时后台任务

虽然运行时先保持单进程，但代码结构仍按 DDD 分层组织。这样后续如果需要把同步任务和投递任务拆成独立 worker 进程，不需要推翻核心 domain 和 application 层设计。

## 高层架构

```text
飞书 API / 企业微信 API / WeLink Mock API
  -> 定时同步任务
  -> ChannelContact / ChannelMessage / SyncCursor
  -> 创建 Delivery
  -> 处理 Delivery
  -> Agent Provider
  -> 渠道回写 / WeLink 群消息发送
```

系统在单个进程里承担两类职责：

1. HTTP 服务职责
   - 健康检查
   - 管理接口
   - 手动触发同步接口

2. 后台执行职责
   - 联系人同步
   - 消息同步
   - delivery 处理

## DDD 分层

### Interfaces 层

负责 FastAPI controller 和对外 HTTP schema。

职责：

- 暴露管理和运维接口
- 校验入参
- 将 HTTP 请求转换为 application command

### Application 层

负责用例编排。

职责：

- 接收同步和投递命令
- 通过 repository 装载和保存领域对象
- 调用领域服务
- 通过 port 调用外部 provider

典型 application service：

- `SyncContactsService`
- `SyncMessagesService`
- `CreateDeliveryService`
- `ProcessDeliveryService`

### Domain 层

负责核心业务概念与规则。

职责：

- 定义核心 entity 和 value object
- 定义 delivery 状态流转
- 定义路由规则
- 定义消息是否可进入 agent 的判定规则

### Infrastructure 层

负责所有外部集成与框架相关实现。

职责：

- 飞书、企业微信 API client
- 持久化实现
- scheduler 注册
- agent WebSocket provider 实现
- 日志与配置

## 核心领域模型

### ChannelAccount

表示一个接入的渠道租户或账号。

核心字段：

- `account_id`
- `channel_type`
- `tenant_id`
- `credentials`
- `enabled`

### ChannelContact

表示从飞书或企业微信同步下来的联系人。

核心字段：

- `contact_id`
- `channel_type`
- `account_id`
- `display_name`
- `is_internal`
- `raw_labels`
- `updated_at`

其中 `is_internal` 是由各渠道原始联系人数据推导出来的统一字段，用于统一表达“内部人员 / 外部人员”。

### ChannelMessage

表示从外部 IM 渠道拉取并规范化后的消息。

核心字段：

- `message_id`
- `channel_type`
- `account_id`
- `conversation_id`
- `sender_id`
- `sender_is_internal`
- `content`
- `sent_at`
- `raw_payload`

### SyncCursor

表示某个渠道账号在某个同步范围下的最近一次同步位点。

核心字段：

- `cursor_id`
- `channel_type`
- `account_id`
- `scope`
- `cursor_payload`
- `updated_at`

其中 `cursor_payload` 明确允许按渠道保存不同结构：

- 企业微信示例：`{ "seq": 123456 }`
- 飞书示例：`{ "container_id": "oc_xxx", "last_message_time": 1712345678, "last_message_id": "om_xxx" }`

这样既保留统一领域模型，又避免强行抽象出一个错误的“通用 cursor 格式”。

### Delivery

表示一条规范化消息被投递到 agent，并可选回写渠道的完整处理过程。

核心字段：

- `delivery_id`
- `message_id`
- `agent_endpoint_id`
- `status`
- `attempt_count`
- `last_error`
- `reply_content`
- `reply_target`
- `created_at`
- `updated_at`

其中 `reply_target` 用于表达回写目标。对飞书、企业微信，它通常对应会话或容器标识；对 WeLink，它对应群消息发送目标。

### AgentEndpoint

表示一个下游 agent 目标。

核心字段：

- `endpoint_id`
- `endpoint_type`
- `base_url`
- `auth_config`
- `timeout_seconds`

### RouteRule

表示一条消息应该如何路由到某个 agent endpoint。

第一版建议支持的路由维度：

- `channel_type`
- `tenant_id`
- 可选的 scene 或 bot 映射

## Delivery 状态模型

`Delivery` 是第一版最核心的生命周期聚合。

建议状态如下：

- `RECEIVED`
- `ROUTED`
- `DISPATCHING`
- `DISPATCHED`
- `REPLYING`
- `SUCCEEDED`
- `FAILED`
- `DEAD`

含义：

- `RECEIVED`：规范化消息已进入系统
- `ROUTED`：已解析出目标 agent endpoint
- `DISPATCHING`：正在调用 agent
- `DISPATCHED`：agent 已成功返回
- `REPLYING`：正在回写渠道
- `SUCCEEDED`：整条链路处理完成
- `FAILED`：处理失败，但允许重试
- `DEAD`：超过最大重试次数

这个状态模型刻意设计成既能支持第一版的“任务表 + 定时处理”，也能自然演进到未来的领域事件：

- `ChannelMessageReceived`
- `DeliveryRouted`
- `AgentDispatchStarted`
- `AgentDispatchSucceeded`
- `ReplyDispatchStarted`
- `ReplyDispatchSucceeded`

## 渠道接入策略

### 企业微信

第一版采用官方“获取会话内容”模型。

建议的同步标识：

- 主增量位点：`seq`
- 去重键：`msgid`

说明：

- 官方文档明确 `seq` 用于增量拉取
- `msgid` 可用于去重
- 外部消息可结合官方消息元数据识别

### 飞书

第一版采用官方“获取会话历史消息”接口。

建议的同步标识：

- 以容器维度维护时间水位
- 使用 `message_id` 做辅助去重
- 单次同步过程中通过 `page_token` 分页

说明：

- 飞书的历史消息接口是按会话容器查询
- 第一版不建议强行抽象成全局 cursor
- 后续如需更实时，再引入事件订阅或长连接

### WeLink

第一版将 WeLink 视为内部接口型渠道，不纳入联系人同步和消息同步链路。

建议定位：

- 作为内部群消息发送通道
- 入参和出参先使用 mock 协议
- 主要承担 delivery 成功后的结果分发，或人工/管理接口触发的群发能力

说明：

- WeLink 第一版只做发送侧能力，不做消息拉取
- 与飞书、企业微信相比，WeLink 更接近一个 outbound channel
- 后续如果需要接入 WeLink 消息读取，再单独扩展 `ChannelMessage` 接入链路

## 运行时设计

第一版运行时保持单个服务进程，但逻辑上拆分后台职责。

### 联系人同步任务

低频执行，例如每 5 到 30 分钟一次。

职责：

- 加载已启用的 `ChannelAccount`
- 拉取飞书或企业微信联系人
- 规范化内外部标记
- upsert `ChannelContact`

### 消息同步任务

高频执行，例如每 5 到 30 秒一次。

职责：

- 读取 `SyncCursor`
- 拉取增量消息
- 规范化并保存 `ChannelMessage`
- 推进 `SyncCursor`
- 为符合条件的消息创建 `Delivery`

### Delivery 处理任务

持续轮询或短间隔轮询执行。

职责：

- 查询待处理 `Delivery`
- 根据 `RouteRule` 解析目标 agent
- 调用 `AgentProvider`
- 更新 delivery 状态
- 如需要则通过飞书、企业微信 API 回写结果，或通过 WeLink mock 接口发送群消息

虽然第一版这些任务在一个进程内运行，但它们应当在 application 层分别建模，避免后续拆独立 worker 时修改核心逻辑。

## Agent Provider 设计

gateway 不应硬编码依赖某一种 agent 实现。

建议在 application/domain 边界定义一个 outbound port：

```python
class AgentProvider(Protocol):
    async def send_message(self, request: SendMessageRequest) -> SendMessageResponse:
        raise NotImplementedError
```

第一版实现：

- `WsAgentProvider`

后续可以扩展：

- 直接模型调用 provider
- 内部 workflow provider
- 其他 agent backend

## Agent WebSocket 协议

`agentgw -> agent` 确认采用 WebSocket，而不是 HTTP 请求响应。

第一版建议采用单连接上的请求响应式消息协议，而不是裸文本推送。

请求帧：

```json
{
  "type": "send_message",
  "request_id": "req_123",
  "channel_type": "wecom",
  "tenant_id": "tenant_1",
  "message_id": "msg_1",
  "conversation_id": "conv_1",
  "sender_id": "user_1",
  "content": "hello",
  "metadata": {}
}
```

响应帧：

```json
{
  "type": "send_message_result",
  "request_id": "req_123",
  "provider_message_id": "agent_msg_1",
  "content": "reply text"
}
```

错误帧：

```json
{
  "type": "send_message_error",
  "request_id": "req_123",
  "error_code": "agent_timeout",
  "error_message": "agent response timed out"
}
```

第一版协议约束：

- 一个 `request_id` 必须只对应一个最终结果帧或错误帧
- `agentgw` 负责维护请求和响应的关联
- 第一版不要求流式 chunk 协议
- 后续如需流式输出，可新增 `send_message_chunk` / `send_message_done` 帧类型

## Agent 连接管理

第一版 `WsAgentProvider` 建议职责如下：

- 建立并复用到 agent 的 WebSocket 连接
- 在连接上发送统一请求帧
- 等待匹配 `request_id` 的结果帧
- 处理超时、断线和重连
- 将协议错误收敛为统一 provider 异常

第一版简化约束：

- 连接管理抽象必须预留多连接能力
- 第一版实现可先采用“单 agent endpoint 小规模连接池”模型
- 单次 `send_message` 仍保持 request-response 语义
- 超时由 `agentgw` 控制，不依赖 agent 端主动断连
- 断线后允许重连，但不自动重放已发送未确认请求

建议的连接管理模型：

- 以 `AgentEndpoint` 为粒度维护连接池
- 每个 endpoint 至少支持配置 `min_connections` 和 `max_connections`
- provider 根据连接可用性和并发情况选择连接发送请求
- 每条连接内部仍通过 `request_id` 做多路复用关联
- 第一版即使只实际创建 1 条连接，代码结构也不能把连接写死成单例

## 项目结构

```text
agentgw/
  pyproject.toml
  uv.lock
  src/agentgw/
    interfaces/
      http/
        controllers/
        schemas/
    application/
      commands/
      dto/
      services/
    domain/
      channel/
      contact/
      message/
      delivery/
      routing/
      agent/
      sync/
    infrastructure/
      persistence/
      channels/
        feishu/
        wecom/
        welink/
      providers/
        agent_ws/
      workers/
      config/
      logging/
    bootstrap/
      container.py
      gateway_app.py
  tests/
    unit/
    integration/
```

## 运维接口

即使消息来自外部渠道 API 拉取，服务本身仍应提供基础运维接口：

- 健康检查
- readiness 检查
- 手动触发某个 account 的联系人同步
- 手动触发某个 account 的消息同步
- 可选的 delivery 重处理接口

这些接口对联调、灰度和排障都很重要。

## 持久化建议

第一版建议采用关系型数据库作为核心状态存储。

建议的基础表：

- `channel_accounts`
- `channel_contacts`
- `channel_messages`
- `sync_cursors`
- `deliveries`
- `route_rules`
- `agent_endpoints`

如果 WeLink 第一版仅承担发送能力，则不需要独立联系人表和消息拉取 cursor；仅需要在 `deliveries` 或后续专门的发送记录表中保留回写目标与发送结果。

这样可以先不引入额外队列基础设施，同时保留足够的可观测性和状态可追踪性。

## 第一版非目标

- 第一版不做独立 worker 部署
- 第一版不强依赖事件总线
- 第一版不做完整会话历史建模，只保留同步和路由所需字段
- 第一版不做高级编排引擎
- 第一版不过度抽象跨渠道统一能力
- 第一版不实现 WeLink 消息拉取，只实现群消息发送 mock

## 演进路径

在不推翻当前设计的前提下，后续可按以下方向演进：

1. 将后台同步和投递任务拆成独立 worker 进程
2. 在 delivery 生命周期中显式产出领域事件
3. 当吞吐和解耦需求足够强时，从任务表轮询演进到队列或事件总线
4. 引入更丰富的会话模型和路由模型

## 最终结论

本次确认的第一版方案为：

- 使用 FastAPI
- 使用 `uv` 管理 Python 项目
- 使用 DDD 风格分层
- 第一版保持单个服务进程
- 在服务内嵌 scheduler，负责联系人同步、消息同步和 delivery 处理
- 通过统一 `SyncCursor` 模型承载各渠道差异化 cursor payload
- 通过可插拔 agent provider 接口对接下游 agent，第一版先落 WebSocket provider
- 将 WeLink 作为内部 outbound channel 接入，第一版只实现 mock 群消息发送
- 整体架构按未来可拆 worker、可演进事件化的方向设计，但第一版不提前引入额外复杂度
