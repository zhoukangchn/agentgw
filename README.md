# agentgw

这个仓库包含 `agentgw` 的架构规格说明文档，以及按规格落地的第一版最小实现。

主文档：

- [2026-04-09-agentgw-channel-centric-spec.md](/home/kangz/project/agentgw/docs/specs/2026-04-09-agentgw-channel-centric-spec.md)
- [2026-04-09-agentgw-implementation.md](/home/kangz/project/agentgw/docs/specs/2026-04-09-agentgw-implementation.md)

仓库范围：

- 以 spec 沉淀目标产品模型
- 提供第一版可运行实现用于联调与验证
- 后续迭代以 spec 和实现文档共同约束演进方向

## 当前可用能力

当前仓库已经可以跑通三条 canonical channel：

- `feishu_ingress`：飞书入站，发送给 `ws_rpc` agent，不做出站
- `feishu_to_welink_group`：飞书入站，发送给 `ws_rpc` agent，最终结果转发到 WeLink 群
- `welink_dm_twoway`：WeLink 私聊入站，发送给 `sdk_session` agent，最终结果回同一个 WeLink 私聊会话

WeLink egress 目前支持两种模式：

- `mock`：只记录出站内容，便于本地联调
- `http`：向真实或模拟的 WeLink HTTP 端点发送消息

## 本地启动

先启动 mock agent：

```bash
uv run python scripts/mock_agent_server.py --host 127.0.0.1 --port 9000
```

再启动 gateway：

```bash
uv run uvicorn agentgw.bootstrap.gateway_app:create_app --factory --host 127.0.0.1 --port 8000
```

默认会使用 SQLite 本地库和 `mock` WeLink egress。

## 关键环境变量

所有配置都使用 `AGENTGW_` 前缀。

```bash
export AGENTGW_DATABASE_URL="sqlite+pysqlite:///./agentgw.db"
export AGENTGW_WS_AGENT_URL="ws://127.0.0.1:9000/ws"
export AGENTGW_SDK_AGENT_URL="ws://127.0.0.1:9000/ws"
export AGENTGW_SDK_MODULE="agentgw.dev.mock_relay_sdk"
```

如果要切到真实 WeLink HTTP egress，再额外配置：

```bash
export AGENTGW_WELINK_ADAPTER_MODE="http"
export AGENTGW_WELINK_BASE_URL="https://welink.example.com"
export AGENTGW_WELINK_ACCESS_TOKEN="replace-me"
export AGENTGW_WELINK_GROUP_MESSAGE_PATH="/groups/{group_id}/messages"
export AGENTGW_WELINK_PRIVATE_MESSAGE_PATH="/dms/{conversation_id}/messages"
```

如果不设置这些变量，`welink_adapter_mode` 默认是 `mock`。

## 联调接口

健康检查：

```bash
curl http://127.0.0.1:8000/healthz
```

查看默认 channel：

```bash
curl http://127.0.0.1:8000/channels
```

手工模拟飞书转 WeLink 群：

```bash
curl -X POST http://127.0.0.1:8000/ingress/events \
  -H 'Content-Type: application/json' \
  -d '{
    "channel_id": "feishu_to_welink_group",
    "source_account_id": "acc-feishu-default",
    "source_conversation_id": "feishu-chat-1",
    "sender_id": "user-1",
    "content": "hello from feishu"
  }'
```

手工模拟 WeLink 私聊双向：

```bash
curl -X POST http://127.0.0.1:8000/ingress/events \
  -H 'Content-Type: application/json' \
  -d '{
    "channel_id": "welink_dm_twoway",
    "source_account_id": "acc-welink-default",
    "source_conversation_id": "welink-dm-1",
    "sender_id": "welink-user-1",
    "content": "hello from welink dm"
  }'
```

查看全链路消息记录：

```bash
curl http://127.0.0.1:8000/messages
```

查看 WeLink egress 结果：

```bash
curl http://127.0.0.1:8000/egress/welink
```

## 验证

运行测试：

```bash
uv run pytest -q -s
```
