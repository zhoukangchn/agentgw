# agentgw channel-centric spec

Date: 2026-04-09

## 1. Purpose

`agentgw` is a business-channel-driven gateway that routes inbound enterprise messages to agent runtimes and optionally forwards agent output to a different outbound channel.

This repository documents the intended product model only. It does not contain a reference implementation.

## 2. Product principles

1. `channel` is a business route, not a platform SDK client.
2. Ingress and egress are independent.
3. Agent transport is independent from business routing.
4. Session capability is explicit, not inferred from platform type.
5. Feishu ingress-only and WeLink DM twoway are both first-class scenarios.

## 3. Core concepts

### 3.1 Channel

A `channel` defines one business routing rule.

Required properties:

- `channel_id`
- `name`
- `ingress`
- `agent`
- `egress`
- `mode`
- `enabled`

### 3.2 Ingress

Defines where inbound messages come from.

Supported initial ingress types:

- `feishu`
- `welink_dm`

Ingress properties:

- `type`
- `account_id`
- optional source-specific config

### 3.3 Agent endpoint

Defines how `agentgw` connects to an agent runtime.

Supported initial transport types:

- `ws_rpc`
- `sdk_session`

Endpoint properties:

- `endpoint_id`
- `name`
- `transport`
- `url`
- `timeout_seconds`
- optional SDK config

### 3.4 Egress

Defines where agent output is sent.

Supported initial egress types:

- `none`
- `welink_group`
- `welink_dm`

Egress properties:

- `type`
- optional `target_id`
- optional `use_source_conversation`

### 3.5 Mode

Channel mode defines interaction shape.

Supported initial modes:

- `ingress_only`
- `oneway`
- `twoway`

Meaning:

- `ingress_only`: inbound is forwarded to agent, agent output is not sent outward
- `oneway`: inbound is forwarded to agent, final agent output is sent to configured egress target
- `twoway`: inbound is forwarded to agent, agent output is sent back into the matching live conversation

### 3.6 Conversation

A `conversation` binds source-side conversation identity to gateway runtime identity.

Properties:

- `conversation_id`
- `channel_id`
- `source_conversation_id`
- `source_user_id`

### 3.7 Message

A `message` is an immutable event record inside the gateway.

Properties:

- `message_id`
- `channel_id`
- `conversation_id`
- `sender_id`
- `direction`
- `content`
- `created_at`

Directions:

- `inbound`
- `agent`
- `egress`

## 4. Canonical business channels

### 4.1 Feishu ingress only

Intent:

- Feishu only provides inbound collection
- Agent output is not sent back to Feishu

Example:

```yaml
channel_id: feishu_ingress
name: Feishu ingress only
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

### 4.2 Feishu to WeLink group

Intent:

- Feishu provides inbound collection
- Agent final output is broadcast to a configured WeLink group

Example:

```yaml
channel_id: feishu_to_welink_group
name: Feishu to WeLink group
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

### 4.3 WeLink DM twoway

Intent:

- WeLink private chat is both ingress and egress
- Agent output returns to the same source conversation

Example:

```yaml
channel_id: welink_dm_twoway
name: WeLink DM twoway
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

## 5. Agent transport contracts

### 5.1 ws_rpc

`ws_rpc` is a request-response protocol on top of a long-lived websocket.

Request:

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

Response:

```json
{
  "type": "send_message_result",
  "request_id": "msg_123",
  "provider_message_id": "agent_msg_123",
  "content": "reply text"
}
```

### 5.2 sdk_session

`sdk_session` is an event-driven session contract using a vendor SDK client.

Expected client shape:

- `async with client`
- `client.on(EventType.*)`
- `send_config(...)`
- `send_message(...)`
- `wait_until_done()`

Expected normalized event categories:

- `agent_call`
- `tool_execution`
- `agent_text`
- `done`
- `error`

## 6. Runtime flow

### 6.1 Common flow

1. Receive inbound event from an ingress adapter.
2. Resolve the target business `channel`.
3. Validate `source_account_id` against channel ingress config.
4. Resolve or create `conversation`.
5. Persist inbound message record.
6. Resolve agent endpoint.
7. Execute the configured agent transport.
8. Persist agent message record.
9. Dispatch output to configured egress target if required.
10. Persist egress message record.

### 6.2 Feishu ingress only

1. Receive Feishu message.
2. Route to `feishu_ingress`.
3. Send to agent endpoint.
4. Persist inbound and agent records.
5. End.

### 6.3 Feishu to WeLink group

1. Receive Feishu message.
2. Route to `feishu_to_welink_group`.
3. Send to agent endpoint.
4. Take final agent output.
5. Send to configured WeLink group.
6. Persist inbound, agent, and egress records.

### 6.4 WeLink DM twoway

1. Receive WeLink private message.
2. Route to `welink_dm_twoway`.
3. Resolve or create conversation mapping.
4. Start agent session using `sdk_session`.
5. Collect session events.
6. Emit final agent output back to the same WeLink conversation.
7. Persist inbound, agent, and egress records.

## 7. Interface requirements

The first HTTP management surface should support:

- list channels
- list agent endpoints
- submit ingress events for manual testing
- inspect recorded messages
- inspect mock egress outputs

This interface is for developer verification and should not define the production ingress contract.

## 8. Persistence requirements

The first production-capable persistence layer should support:

- channel configuration storage
- agent endpoint storage
- conversation mapping storage
- message record storage

Recommended tables:

- `channels`
- `agent_endpoints`
- `conversations`
- `messages`

## 9. Non-goals for this spec

This spec does not define:

- production Feishu API integration details
- production WeLink API integration details
- auth secret management details
- retry semantics for every adapter
- deployment topology

## 10. Implementation sequencing

Recommended implementation order:

1. Channel configuration and endpoint persistence
2. Runtime orchestration and normalized message model
3. `ws_rpc` agent transport
4. `sdk_session` agent transport
5. WeLink group egress
6. WeLink DM egress
7. Feishu ingress adapter
8. WeLink DM ingress adapter
