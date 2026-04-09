# Agent session integration design

Date: 2026-04-09

## Problem

`agentgw` currently has two different needs:

1. RPC-style agents: gw sends one request and waits for one response.
2. Session-style agents: gw opens a live websocket session, receives push events, and only finishes when the session reports completion.

The SDK example provided by the user is session-style:
- `async with client`
- `@client.on(EventType.*)` callbacks
- `send_config(...)`
- `send_message(...)`
- `wait_until_done()`

## Design goal

Keep the current `send_message(...)` path stable, while making room for session-oriented agents without forcing all agents into the same API.

## Proposed split

### 1. AgentProvider
RPC facade.

Use for the existing websocket request/response behavior.

- `send_message(request) -> response`
- no session lifecycle required
- backward compatible with current delivery flow

### 2. AgentSession
Event-driven session facade.

Use for SDK-style agents that keep a connection open and emit events over time.

Suggested capabilities:
- async context manager lifecycle
- event subscriptions
- `send_config(...)`
- `send_message(...)`
- `wait_until_done()`
- `close()`

### 3. AgentEndpoint
Store which transport shape an endpoint uses.

Suggested `endpoint_type` values:
- `ws_rpc`
- `relay_sdk`

## Event model

Introduce a normalized internal event shape so the application layer does not need to know SDK-specific event classes.

Suggested fields:
- `session_id`
- `event_type`
- `payload`
- `raw_payload`
- `created_at`

## Mapping strategy

The SDK’s raw events should be mapped into `AgentEventType` values such as:
- `agent_call`
- `agent_text`
- `tool_execution`
- `done`
- `error`
- `debug`

## Integration path

1. Keep the existing `WebSocketAgentProvider` for RPC-style usage.
2. Add a session adapter that wraps the SDK client.
3. Add a factory that selects provider/session implementation based on `AgentEndpoint.endpoint_type`.
4. In application code, use the RPC provider for current delivery processing and the session adapter for long-running conversations.

## Risks

- The SDK event schema may differ from the user’s example, so the adapter should accept a mapping layer.
- Event handlers should not silently swallow exceptions in production; they should be logged or surfaced.
- If the same connection is used for both RPC and session event streaming, request correlation and background reads must not compete for `recv()`.

## Next step

Wire a factory into bootstrap once a concrete SDK package name and endpoint configuration are available.
