# Agent Gateway Channel Gateway Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建一个基于 FastAPI、DDD 分层、单进程内嵌 scheduler 的 agent gateway，支持飞书/企业微信联系人同步、消息同步、Delivery 创建与 WebSocket agent 投递，并支持内部 WeLink mock 群消息发送的第一版最小闭环。

**Architecture:** 使用单仓库、单进程 FastAPI 服务，按 `interfaces / application / domain / infrastructure` 分层。联系人同步、消息同步、delivery 处理先以内嵌 scheduler 运行，持久化使用关系型数据库，agent 对接通过可插拔 provider 抽象，第一版先落地 WebSocket provider。

**Tech Stack:** Python 3.12, uv, FastAPI, Pydantic, SQLAlchemy, Alembic, websockets, pytest

---

## File Structure

本计划将创建如下文件结构，并按职责拆分：

- `pyproject.toml`
  项目依赖、`uv` 配置、脚本入口
- `src/agentgw/bootstrap/gateway_app.py`
  FastAPI 应用装配入口
- `src/agentgw/bootstrap/container.py`
  依赖装配与服务注册
- `src/agentgw/interfaces/http/controllers/health.py`
  健康检查接口
- `src/agentgw/interfaces/http/controllers/admin_sync.py`
  手动触发同步接口
- `src/agentgw/interfaces/http/schemas/admin_sync.py`
  管理接口 schema
- `src/agentgw/application/dto/messages.py`
  应用层统一 DTO
- `src/agentgw/application/services/sync_contacts.py`
  联系人同步用例
- `src/agentgw/application/services/sync_messages.py`
  消息同步用例
- `src/agentgw/application/services/process_delivery.py`
  Delivery 处理用例
- `src/agentgw/domain/channel/entities.py`
  `ChannelAccount`
- `src/agentgw/domain/contact/entities.py`
  `ChannelContact`
- `src/agentgw/domain/message/entities.py`
  `ChannelMessage`
- `src/agentgw/domain/delivery/entities.py`
  `Delivery` 与状态流转
- `src/agentgw/domain/agent/entities.py`
  `AgentEndpoint`
- `src/agentgw/domain/routing/entities.py`
  `RouteRule`
- `src/agentgw/domain/sync/entities.py`
  `SyncCursor`
- `src/agentgw/domain/delivery/repositories.py`
  Delivery 仓储接口
- `src/agentgw/domain/channel/repositories.py`
  ChannelAccount 仓储接口
- `src/agentgw/domain/contact/repositories.py`
  Contact 仓储接口
- `src/agentgw/domain/message/repositories.py`
  Message 仓储接口
- `src/agentgw/domain/routing/repositories.py`
  RouteRule 仓储接口
- `src/agentgw/domain/agent/repositories.py`
  AgentEndpoint 仓储接口
- `src/agentgw/domain/sync/repositories.py`
  SyncCursor 仓储接口
- `src/agentgw/domain/agent/providers.py`
  AgentProvider port
- `src/agentgw/infrastructure/config/settings.py`
  配置加载
- `src/agentgw/infrastructure/persistence/base.py`
  SQLAlchemy Base / session 工厂
- `src/agentgw/infrastructure/persistence/models.py`
  ORM 模型
- `src/agentgw/infrastructure/persistence/repositories/*.py`
  各领域仓储实现
- `src/agentgw/infrastructure/providers/agent_ws/provider.py`
  WebSocket agent provider
- `src/agentgw/infrastructure/channels/feishu/client.py`
  飞书 API client 骨架
- `src/agentgw/infrastructure/channels/wecom/client.py`
  企业微信 API client 骨架
- `src/agentgw/infrastructure/channels/welink/client.py`
  WeLink mock 群消息 client
- `src/agentgw/infrastructure/workers/scheduler.py`
  scheduler 注册
- `src/agentgw/infrastructure/workers/jobs.py`
  定时任务入口
- `tests/unit/domain/test_delivery.py`
  Delivery 状态流转测试
- `tests/unit/application/test_sync_messages.py`
  消息同步用例测试
- `tests/unit/application/test_process_delivery.py`
  Delivery 处理用例测试
- `tests/unit/infrastructure/test_models.py`
  持久化模型 smoke test
- `tests/integration/test_health_api.py`
  FastAPI 健康检查集成测试
- `tests/integration/test_admin_sync_api.py`
  管理接口集成测试

### Task 1: 初始化项目骨架

**Files:**
- Create: `pyproject.toml`
- Create: `src/agentgw/__init__.py`
- Create: `src/agentgw/bootstrap/gateway_app.py`
- Create: `src/agentgw/bootstrap/container.py`
- Create: `src/agentgw/interfaces/http/controllers/health.py`
- Create: `tests/integration/test_health_api.py`

- [ ] **Step 1: 写健康检查集成测试**

```python
from fastapi.testclient import TestClient

from agentgw.bootstrap.gateway_app import create_app


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `uv run pytest tests/integration/test_health_api.py -v`
Expected: FAIL，因为 `agentgw.bootstrap.gateway_app` 或 `create_app` 尚不存在

- [ ] **Step 3: 编写 `pyproject.toml` 和最小应用骨架**

```toml
[project]
name = "agentgw"
version = "0.1.0"
description = "Agent gateway for Feishu and WeCom channel sync"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn>=0.30.0",
  "pydantic>=2.8.0",
  "pydantic-settings>=2.4.0",
  "sqlalchemy>=2.0.32",
  "alembic>=1.13.2",
  "httpx>=0.27.0",
  "pytest>=8.3.2",
]

[tool.pytest.ini_options]
pythonpath = ["src"]

[project.scripts]
gateway = "agentgw.bootstrap.gateway_app:run"
```
```python
# src/agentgw/bootstrap/gateway_app.py
from fastapi import FastAPI

from agentgw.interfaces.http.controllers.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="agentgw")
    app.include_router(health_router)
    return app


def run() -> None:
    import uvicorn

    uvicorn.run("agentgw.bootstrap.gateway_app:create_app", factory=True, host="0.0.0.0", port=8000)
```
```python
# src/agentgw/interfaces/http/controllers/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `uv run pytest tests/integration/test_health_api.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add pyproject.toml src/agentgw tests/integration/test_health_api.py
git commit -m "feat: scaffold FastAPI gateway app"
```

### Task 2: 建立核心领域模型与状态机

**Files:**
- Create: `src/agentgw/domain/channel/entities.py`
- Create: `src/agentgw/domain/contact/entities.py`
- Create: `src/agentgw/domain/message/entities.py`
- Create: `src/agentgw/domain/delivery/entities.py`
- Create: `src/agentgw/domain/agent/entities.py`
- Create: `src/agentgw/domain/routing/entities.py`
- Create: `src/agentgw/domain/sync/entities.py`
- Test: `tests/unit/domain/test_delivery.py`

- [ ] **Step 1: 编写 Delivery 状态流转测试**

```python
import pytest

from agentgw.domain.delivery.entities import Delivery, DeliveryStatus


def test_delivery_can_move_from_received_to_routed() -> None:
    delivery = Delivery.create(message_id="msg-1")

    delivery.mark_routed(agent_endpoint_id="agent-1")

    assert delivery.status is DeliveryStatus.ROUTED
    assert delivery.agent_endpoint_id == "agent-1"


def test_delivery_rejects_invalid_transition() -> None:
    delivery = Delivery.create(message_id="msg-1")

    with pytest.raises(ValueError, match="invalid delivery transition"):
        delivery.mark_succeeded("done")
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `uv run pytest tests/unit/domain/test_delivery.py -v`
Expected: FAIL，因为 `Delivery` 和 `DeliveryStatus` 尚不存在

- [ ] **Step 3: 实现领域实体与 Delivery 状态机**

```python
# src/agentgw/domain/delivery/entities.py
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class DeliveryStatus(str, Enum):
    RECEIVED = "RECEIVED"
    ROUTED = "ROUTED"
    DISPATCHING = "DISPATCHING"
    DISPATCHED = "DISPATCHED"
    REPLYING = "REPLYING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    DEAD = "DEAD"


@dataclass
class Delivery:
    message_id: str
    delivery_id: str | None = None
    agent_endpoint_id: str | None = None
    status: DeliveryStatus = DeliveryStatus.RECEIVED
    attempt_count: int = 0
    last_error: str | None = None
    reply_content: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(cls, message_id: str) -> "Delivery":
        return cls(message_id=message_id)

    def mark_routed(self, agent_endpoint_id: str) -> None:
        if self.status is not DeliveryStatus.RECEIVED:
            raise ValueError("invalid delivery transition")
        self.agent_endpoint_id = agent_endpoint_id
        self.status = DeliveryStatus.ROUTED
        self.updated_at = datetime.now(UTC)

    def mark_succeeded(self, reply_content: str) -> None:
        if self.status not in {DeliveryStatus.DISPATCHED, DeliveryStatus.REPLYING}:
            raise ValueError("invalid delivery transition")
        self.reply_content = reply_content
        self.status = DeliveryStatus.SUCCEEDED
        self.updated_at = datetime.now(UTC)
```

- [ ] **Step 4: 为其他领域对象补充最小 dataclass**

```python
# src/agentgw/domain/message/entities.py
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ChannelMessage:
    message_id: str
    channel_type: str
    account_id: str
    conversation_id: str
    sender_id: str
    sender_is_internal: bool
    content: str
    sent_at: datetime
    raw_payload: dict
```

- [ ] **Step 5: 运行测试，确认通过**

Run: `uv run pytest tests/unit/domain/test_delivery.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add src/agentgw/domain tests/unit/domain/test_delivery.py
git commit -m "feat: add core domain entities"
```

### Task 3: 定义仓储接口、DTO 与 AgentProvider port

**Files:**
- Create: `src/agentgw/domain/channel/repositories.py`
- Create: `src/agentgw/domain/contact/repositories.py`
- Create: `src/agentgw/domain/message/repositories.py`
- Create: `src/agentgw/domain/delivery/repositories.py`
- Create: `src/agentgw/domain/routing/repositories.py`
- Create: `src/agentgw/domain/agent/repositories.py`
- Create: `src/agentgw/domain/sync/repositories.py`
- Create: `src/agentgw/domain/agent/providers.py`
- Create: `src/agentgw/application/dto/messages.py`

- [ ] **Step 1: 为应用层定义统一 DTO**

```python
from dataclasses import dataclass, field


@dataclass
class SendMessageRequest:
    request_id: str
    channel_type: str
    tenant_id: str
    message_id: str
    sender_id: str
    conversation_id: str
    content: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class SendMessageResponse:
    provider_message_id: str
    content: str
```

- [ ] **Step 2: 定义 AgentProvider port**

```python
from typing import Protocol

from agentgw.application.dto.messages import SendMessageRequest, SendMessageResponse


class AgentProvider(Protocol):
    async def send_message(self, request: SendMessageRequest) -> SendMessageResponse:
        raise NotImplementedError
```

- [ ] **Step 3: 定义领域仓储接口**

```python
from typing import Protocol

from agentgw.domain.delivery.entities import Delivery


class DeliveryRepository(Protocol):
    async def save(self, delivery: Delivery) -> Delivery:
        raise NotImplementedError

    async def list_pending(self, limit: int = 100) -> list[Delivery]:
        raise NotImplementedError
```

- [ ] **Step 4: 运行基础导入检查**

Run: `uv run python -c "from agentgw.domain.agent.providers import AgentProvider; print('ok')"`
Expected: 输出 `ok`

- [ ] **Step 5: 提交**

```bash
git add src/agentgw/domain/*/repositories.py src/agentgw/domain/agent/providers.py src/agentgw/application/dto/messages.py
git commit -m "feat: define ports and dto contracts"
```

### Task 4: 建立持久化层与 ORM 映射

**Files:**
- Create: `src/agentgw/infrastructure/persistence/base.py`
- Create: `src/agentgw/infrastructure/persistence/models.py`
- Create: `src/agentgw/infrastructure/persistence/repositories/delivery.py`
- Create: `src/agentgw/infrastructure/persistence/repositories/message.py`
- Create: `src/agentgw/infrastructure/persistence/repositories/contact.py`
- Create: `src/agentgw/infrastructure/persistence/repositories/channel.py`
- Create: `src/agentgw/infrastructure/persistence/repositories/sync.py`
- Create: `src/agentgw/infrastructure/persistence/repositories/routing.py`
- Create: `src/agentgw/infrastructure/persistence/repositories/agent.py`
- Create: `tests/unit/infrastructure/test_models.py`

- [ ] **Step 1: 为数据库连接写最小 smoke test**

```python
from sqlalchemy import inspect

from agentgw.infrastructure.persistence.base import Base, engine
from agentgw.infrastructure.persistence.models import DeliveryModel


def test_delivery_table_is_registered() -> None:
    tables = inspect(Base.metadata)
    assert "deliveries" in tables.tables
    assert DeliveryModel.__tablename__ == "deliveries"
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `uv run pytest tests/unit/infrastructure/test_models.py -v`
Expected: FAIL，因为持久化层尚不存在

- [ ] **Step 3: 建立 SQLAlchemy Base 与核心 ORM 模型**

```python
# src/agentgw/infrastructure/persistence/base.py
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
```
```python
# src/agentgw/infrastructure/persistence/models.py
from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from agentgw.infrastructure.persistence.base import Base


class DeliveryModel(Base):
    __tablename__ = "deliveries"

    delivery_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    message_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    agent_endpoint_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    reply_content: Mapped[str | None] = mapped_column(Text)
```

- [ ] **Step 4: 编写 DeliveryRepository 的 SQLAlchemy 实现**

```python
class SqlAlchemyDeliveryRepository:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def list_pending(self, limit: int = 100) -> list[Delivery]:
        with self._session_factory() as session:
            rows = (
                session.query(DeliveryModel)
                .filter(DeliveryModel.status.in_(["RECEIVED", "ROUTED", "FAILED"]))
                .limit(limit)
                .all()
            )
            return [Delivery(message_id=row.message_id, delivery_id=row.delivery_id) for row in rows]
```

- [ ] **Step 5: 运行测试，确认通过**

Run: `uv run pytest tests/unit/infrastructure/test_models.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add src/agentgw/infrastructure/persistence tests/unit/infrastructure/test_models.py
git commit -m "feat: add persistence base and repositories"
```

### Task 5: 实现消息同步应用服务

**Files:**
- Create: `src/agentgw/application/services/sync_messages.py`
- Test: `tests/unit/application/test_sync_messages.py`

- [ ] **Step 1: 写消息同步用例测试**

```python
import pytest

from agentgw.application.services.sync_messages import SyncMessagesService
from agentgw.domain.delivery.entities import Delivery
from agentgw.domain.message.entities import ChannelMessage


class FakeChannelClient:
    async def fetch_messages(self, account_id: str, cursor_payload: dict) -> tuple[list[ChannelMessage], dict]:
        return (
            [
                ChannelMessage(
                    message_id="msg-1",
                    channel_type="wecom",
                    account_id=account_id,
                    conversation_id="conv-1",
                    sender_id="user-1",
                    sender_is_internal=False,
                    content="hello",
                    sent_at=__import__("datetime").datetime.now(),
                    raw_payload={},
                )
            ],
            {"seq": 10},
        )


class FakeCursor:
    def __init__(self, cursor_payload: dict):
        self.cursor_payload = cursor_payload


class FakeCursorRepository:
    def __init__(self):
        self.saved_payload: dict | None = None

    async def get_for_scope(self, account_id: str, scope: str) -> FakeCursor:
        return FakeCursor({"seq": 0})

    async def upsert(self, account_id: str, scope: str, payload: dict) -> None:
        self.saved_payload = payload


class FakeMessageRepository:
    def __init__(self):
        self.saved_messages: list[ChannelMessage] = []

    async def save(self, message: ChannelMessage) -> ChannelMessage:
        self.saved_messages.append(message)
        return message


class FakeDeliveryRepository:
    def __init__(self):
        self.saved_deliveries: list[Delivery] = []

    async def save(self, delivery: Delivery) -> Delivery:
        self.saved_deliveries.append(delivery)
        return delivery


@pytest.mark.asyncio
async def test_sync_messages_persists_message_and_updates_cursor() -> None:
    cursor_repository = FakeCursorRepository()
    message_repository = FakeMessageRepository()
    delivery_repository = FakeDeliveryRepository()
    service = SyncMessagesService(
        channel_client=FakeChannelClient(),
        cursor_repository=cursor_repository,
        message_repository=message_repository,
        delivery_repository=delivery_repository,
    )

    result = await service.sync_account("acc-1")

    assert result.synced_count == 1
    assert result.next_cursor == {"seq": 10}
    assert cursor_repository.saved_payload == {"seq": 10}
    assert len(message_repository.saved_messages) == 1
    assert len(delivery_repository.saved_deliveries) == 1
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `uv run pytest tests/unit/application/test_sync_messages.py -v`
Expected: FAIL，因为 `SyncMessagesService` 尚不存在

- [ ] **Step 3: 实现消息同步用例**

```python
from dataclasses import dataclass


@dataclass
class SyncMessagesResult:
    synced_count: int
    next_cursor: dict


class SyncMessagesService:
    def __init__(self, channel_client, cursor_repository, message_repository, delivery_repository):
        self._channel_client = channel_client
        self._cursor_repository = cursor_repository
        self._message_repository = message_repository
        self._delivery_repository = delivery_repository

    async def sync_account(self, account_id: str) -> SyncMessagesResult:
        cursor = await self._cursor_repository.get_for_scope(account_id, "messages")
        messages, next_cursor = await self._channel_client.fetch_messages(account_id, cursor.cursor_payload if cursor else {})

        for message in messages:
            await self._message_repository.save(message)
            await self._delivery_repository.save(Delivery.create(message.message_id))

        await self._cursor_repository.upsert(account_id, "messages", next_cursor)
        return SyncMessagesResult(synced_count=len(messages), next_cursor=next_cursor)
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `uv run pytest tests/unit/application/test_sync_messages.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/agentgw/application/services/sync_messages.py tests/unit/application/test_sync_messages.py
git commit -m "feat: implement message sync workflow"
```

### Task 6: 实现 Delivery 处理用例与 WebSocket agent provider

**Files:**
- Create: `src/agentgw/application/services/process_delivery.py`
- Create: `src/agentgw/infrastructure/providers/agent_ws/provider.py`
- Test: `tests/unit/application/test_process_delivery.py`

- [ ] **Step 1: 写 Delivery 处理测试**

```python
import pytest

from agentgw.application.dto.messages import SendMessageResponse
from agentgw.application.services.process_delivery import ProcessDeliveryService
from agentgw.domain.message.entities import ChannelMessage
from agentgw.domain.delivery.entities import Delivery, DeliveryStatus


class FakeAgentProvider:
    async def send_message(self, request):
        return SendMessageResponse(provider_message_id="p-1", content="reply")


class FakeMessageRepository:
    async def get_by_message_id(self, message_id: str) -> ChannelMessage:
        return ChannelMessage(
            message_id=message_id,
            channel_type="wecom",
            account_id="tenant-1",
            conversation_id="conv-1",
            sender_id="user-1",
            sender_is_internal=False,
            content="hello",
            sent_at=__import__("datetime").datetime.now(),
            raw_payload={},
        )


class FakeDeliveryRepository:
    def __init__(self):
        self.saved_delivery: Delivery | None = None

    async def save(self, delivery: Delivery) -> Delivery:
        self.saved_delivery = delivery
        return delivery


@pytest.mark.asyncio
async def test_process_delivery_marks_success() -> None:
    delivery = Delivery.create(message_id="msg-1")
    delivery.mark_routed("agent-1")
    delivery.status = DeliveryStatus.DISPATCHED

    delivery_repository = FakeDeliveryRepository()
    service = ProcessDeliveryService(
        agent_provider=FakeAgentProvider(),
        message_repository=FakeMessageRepository(),
        delivery_repository=delivery_repository,
    )

    updated = await service.process(delivery)

    assert updated.status is DeliveryStatus.SUCCEEDED
    assert updated.reply_content == "reply"
    assert delivery_repository.saved_delivery is updated
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `uv run pytest tests/unit/application/test_process_delivery.py -v`
Expected: FAIL，因为 `ProcessDeliveryService` 尚不存在

- [ ] **Step 3: 实现 Delivery 处理用例**

```python
class ProcessDeliveryService:
    def __init__(self, agent_provider, message_repository, delivery_repository):
        self._agent_provider = agent_provider
        self._message_repository = message_repository
        self._delivery_repository = delivery_repository

    async def process(self, delivery: Delivery) -> Delivery:
        message = await self._message_repository.get_by_message_id(delivery.message_id)
        response = await self._agent_provider.send_message(
            SendMessageRequest(
                request_id=delivery.delivery_id or delivery.message_id,
                channel_type=message.channel_type,
                tenant_id=message.account_id,
                message_id=message.message_id,
                sender_id=message.sender_id,
                conversation_id=message.conversation_id,
                content=message.content,
            )
        )
        delivery.mark_succeeded(response.content)
        await self._delivery_repository.save(delivery)
        return delivery
```

- [ ] **Step 4: 实现 WebSocket agent provider**

```python
import asyncio
import json

import websockets

from agentgw.domain.agent.contracts import SendMessageRequest, SendMessageResponse


class WsAgentProvider:
    def __init__(self, base_url: str, timeout_seconds: int = 10):
        self._base_url = base_url
        self._timeout_seconds = timeout_seconds
        self._connections = []

    async def send_message(self, request: SendMessageRequest) -> SendMessageResponse:
        websocket = await self._acquire_connection()
        await websocket.send(
            json.dumps(
                {
                    "type": "send_message",
                    "request_id": request.request_id,
                    "channel_type": request.channel_type,
                    "tenant_id": request.tenant_id,
                    "message_id": request.message_id,
                    "conversation_id": request.conversation_id,
                    "sender_id": request.sender_id,
                    "content": request.content,
                    "metadata": request.metadata,
                }
            )
        )
        raw = await asyncio.wait_for(websocket.recv(), timeout=self._timeout_seconds)
        payload = json.loads(raw)
        return SendMessageResponse(
            provider_message_id=payload["provider_message_id"],
            content=payload["content"],
        )

    async def _acquire_connection(self):
        if self._connections:
            return self._connections[0]
        websocket = await websockets.connect(self._base_url)
        self._connections.append(websocket)
        return websocket
```

- [ ] **Step 5: 运行测试，确认通过**

Run: `uv run pytest tests/unit/application/test_process_delivery.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add src/agentgw/application/services/process_delivery.py src/agentgw/infrastructure/providers/agent_ws/provider.py tests/unit/application/test_process_delivery.py
git commit -m "feat: implement delivery processing and ws agent provider"
```

### Task 7: 实现 WeLink mock 群消息发送能力

**Files:**
- Create: `src/agentgw/infrastructure/channels/welink/client.py`
- Modify: `src/agentgw/application/services/process_delivery.py`
- Test: `tests/unit/application/test_process_delivery.py`

- [ ] **Step 1: 先补一条 WeLink 发送分支测试**

```python
import pytest

from agentgw.application.dto.messages import SendMessageResponse
from agentgw.application.services.process_delivery import ProcessDeliveryService
from agentgw.domain.delivery.entities import Delivery, DeliveryStatus
from agentgw.domain.message.entities import ChannelMessage


class FakeWeLinkClient:
    def __init__(self):
        self.calls: list[dict] = []

    async def send_group_message(self, group_id: str, content: str) -> dict:
        self.calls.append({"group_id": group_id, "content": content})
        return {"code": 0, "message": "ok", "request_id": "welink-1"}


class FakeMessageRepository:
    async def get_by_message_id(self, message_id: str) -> ChannelMessage:
        return ChannelMessage(
            message_id=message_id,
            channel_type="welink",
            account_id="tenant-1",
            conversation_id="group-1",
            sender_id="user-1",
            sender_is_internal=True,
            content="notify team",
            sent_at=__import__("datetime").datetime.now(),
            raw_payload={},
        )


@pytest.mark.asyncio
async def test_process_delivery_sends_group_message_to_welink() -> None:
    delivery = Delivery.create(message_id="msg-1")
    delivery.mark_routed("agent-1")
    delivery.status = DeliveryStatus.DISPATCHED

    welink_client = FakeWeLinkClient()
    service = ProcessDeliveryService(
        agent_provider=FakeAgentProvider(),
        message_repository=FakeMessageRepository(),
        delivery_repository=FakeDeliveryRepository(),
        welink_client=welink_client,
    )

    updated = await service.process(delivery)

    assert updated.status is DeliveryStatus.SUCCEEDED
    assert welink_client.calls == [{"group_id": "group-1", "content": "reply"}]
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `uv run pytest tests/unit/application/test_process_delivery.py -v`
Expected: FAIL，因为 `ProcessDeliveryService` 还没有 WeLink 分支和 `welink_client` 依赖

- [ ] **Step 3: 实现 WeLink mock client**

```python
class WeLinkClient:
    async def send_group_message(self, group_id: str, content: str) -> dict:
        return {
            "code": 0,
            "message": "ok",
            "request_id": "mock-welink-request-id",
            "group_id": group_id,
            "content": content,
        }
```

- [ ] **Step 4: 在 Delivery 处理用例里接入 WeLink 分支**

```python
class ProcessDeliveryService:
    def __init__(self, agent_provider, message_repository, delivery_repository, welink_client=None):
        self._agent_provider = agent_provider
        self._message_repository = message_repository
        self._delivery_repository = delivery_repository
        self._welink_client = welink_client

    async def process(self, delivery: Delivery) -> Delivery:
        message = await self._message_repository.get_by_message_id(delivery.message_id)
        response = await self._agent_provider.send_message(
            SendMessageRequest(
                request_id=delivery.delivery_id or delivery.message_id,
                channel_type=message.channel_type,
                tenant_id=message.account_id,
                message_id=message.message_id,
                sender_id=message.sender_id,
                conversation_id=message.conversation_id,
                content=message.content,
            )
        )

        if message.channel_type == "welink" and self._welink_client is not None:
            await self._welink_client.send_group_message(
                group_id=message.conversation_id,
                content=response.content,
            )

        delivery.mark_succeeded(response.content)
        await self._delivery_repository.save(delivery)
        return delivery
```

- [ ] **Step 5: 运行测试，确认通过**

Run: `uv run pytest tests/unit/application/test_process_delivery.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add src/agentgw/infrastructure/channels/welink/client.py src/agentgw/application/services/process_delivery.py tests/unit/application/test_process_delivery.py
git commit -m "feat: add mock welink group message sending"
```

### Task 8: 实现联系人同步、调度器和管理接口

**Files:**
- Create: `src/agentgw/application/services/sync_contacts.py`
- Create: `src/agentgw/interfaces/http/schemas/admin_sync.py`
- Create: `src/agentgw/interfaces/http/controllers/admin_sync.py`
- Create: `src/agentgw/infrastructure/workers/jobs.py`
- Create: `src/agentgw/infrastructure/workers/scheduler.py`
- Modify: `src/agentgw/bootstrap/gateway_app.py`
- Create: `tests/integration/test_admin_sync_api.py`

- [ ] **Step 1: 为管理接口写测试**

```python
from fastapi.testclient import TestClient

from agentgw.bootstrap.gateway_app import create_app


def test_admin_sync_endpoint_accepts_request() -> None:
    client = TestClient(create_app())

    response = client.post("/admin/sync/messages", json={"account_id": "acc-1"})

    assert response.status_code == 202
    assert response.json() == {"accepted": True, "account_id": "acc-1"}
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `uv run pytest tests/integration/test_admin_sync_api.py -v`
Expected: FAIL，因为管理接口尚不存在

- [ ] **Step 3: 实现联系人同步用例与管理接口**

```python
# src/agentgw/interfaces/http/schemas/admin_sync.py
from pydantic import BaseModel


class TriggerSyncRequest(BaseModel):
    account_id: str
```
```python
# src/agentgw/interfaces/http/controllers/admin_sync.py
from fastapi import APIRouter, status

from agentgw.interfaces.http.schemas.admin_sync import TriggerSyncRequest

router = APIRouter(prefix="/admin/sync", tags=["admin-sync"])


@router.post("/messages", status_code=status.HTTP_202_ACCEPTED)
async def trigger_message_sync(request: TriggerSyncRequest) -> dict[str, object]:
    return {"accepted": True, "account_id": request.account_id}
```

- [ ] **Step 4: 实现 scheduler 与 job 入口**

```python
class Scheduler:
    def __init__(self, sync_contacts_job, sync_messages_job, process_deliveries_job):
        self._jobs = [sync_contacts_job, sync_messages_job, process_deliveries_job]

    async def start(self) -> None:
        for job in self._jobs:
            await job()
```

- [ ] **Step 5: 在应用启动时注册 scheduler**

```python
def create_app() -> FastAPI:
    app = FastAPI(title="agentgw")
    app.include_router(health_router)
    app.include_router(admin_sync_router)

    @app.on_event("startup")
    async def startup_scheduler() -> None:
        scheduler = build_scheduler()
        await scheduler.start()

    return app
```

- [ ] **Step 6: 运行相关测试**

Run: `uv run pytest tests/integration/test_health_api.py tests/integration/test_admin_sync_api.py -v`
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add src/agentgw/application/services/sync_contacts.py src/agentgw/interfaces/http src/agentgw/infrastructure/workers src/agentgw/bootstrap/gateway_app.py tests/integration/test_admin_sync_api.py
git commit -m "feat: add scheduler and admin sync endpoints"
```

### Task 9: 贯通装配、配置与全量验证

**Files:**
- Create: `src/agentgw/infrastructure/config/settings.py`
- Modify: `src/agentgw/bootstrap/container.py`
- Modify: `src/agentgw/bootstrap/gateway_app.py`

- [ ] **Step 1: 实现配置对象**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "agentgw"
    database_url: str = "sqlite+pysqlite:///./agentgw.db"
    agent_base_url: str = "ws://localhost:9000/ws"
    message_sync_interval_seconds: int = 10
    contact_sync_interval_seconds: int = 300

    model_config = SettingsConfigDict(env_prefix="AGENTGW_", extra="ignore")
```

- [ ] **Step 2: 在 container 中集中装配依赖**

```python
from agentgw.infrastructure.config.settings import Settings
from agentgw.infrastructure.providers.agent_ws.provider import WsAgentProvider


def build_container() -> dict[str, object]:
    settings = Settings()
    return {
        "settings": settings,
        "agent_provider": WsAgentProvider(settings.agent_base_url),
    }
```

- [ ] **Step 3: 运行全量测试**

Run: `uv run pytest -v`
Expected: 所有单元测试与集成测试通过

- [ ] **Step 4: 做一次启动验证**

Run: `uv run gateway`
Expected: 服务成功启动，并监听 `0.0.0.0:8000`

- [ ] **Step 5: 提交**

```bash
git add src/agentgw/infrastructure/config/settings.py src/agentgw/bootstrap/container.py src/agentgw/bootstrap/gateway_app.py
git commit -m "feat: wire configuration and application container"
```
