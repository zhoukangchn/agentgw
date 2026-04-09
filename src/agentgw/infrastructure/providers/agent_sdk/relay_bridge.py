from __future__ import annotations

import asyncio
import inspect
import json
import logging
from contextlib import suppress
from typing import Any, AsyncGenerator, Awaitable, Callable

from fastapi import Request

from agentgw.domain.agent.events import AgentEventType

logger = logging.getLogger("agentgw.relay_sdk")

DEFAULT_TIMEOUT_SECONDS = 60


def format_sse(data: Any, event: str | None = None) -> str:
    lines: list[str] = []
    if event:
        lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data, ensure_ascii=False)}")
    return "\n".join(lines) + "\n\n"


def safe_get(obj: Any, name: str, default: Any = None) -> Any:
    return getattr(obj, name, default)


def dump_event(event: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name in dir(event):
        if name.startswith("_"):
            continue
        try:
            value = getattr(event, name)
            if callable(value):
                continue
            result[name] = value
        except Exception:
            result[name] = "<unreadable>"
    return result


class RelaySdkBridge:
    def __init__(
        self,
        *,
        ws_url: str,
        message: str,
        project_home: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        client: Any | None = None,
        client_factory: Callable[[str], Any] | None = None,
        event_type: Any | None = None,
        event_sink: Callable[[str, dict[str, Any]], Awaitable[None] | None] | None = None,
    ) -> None:
        if client is None and client_factory is None:
            raise ValueError("client or client_factory is required")

        self.ws_url = ws_url
        self.message = message
        self.project_home = project_home
        self.timeout_seconds = timeout_seconds
        self.client = client or client_factory(ws_url)
        self.event_type = event_type
        self.event_sink = event_sink
        self.queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
        self._registered = False
        self._register_handlers()

    async def _emit(self, event: str, data: dict[str, Any]) -> None:
        logger.info("emit event=%s data=%s", event, data)
        if self.event_sink is not None:
            result = self.event_sink(event, data)
            if inspect.isawaitable(result):
                await result
        await self.queue.put((event, data))

    def _register_handlers(self) -> None:
        if self._registered:
            return
        if self.event_type is None:
            raise ValueError("event_type is required")

        logger.info("开始注册 RelayClient 事件处理器")

        @self.client.on(self.event_type.AGENT_CALL)
        async def on_agent_call(event: Any) -> None:
            payload = {
                "agent_name": safe_get(event, "agent_name", "unknown"),
                "is_start": bool(safe_get(event, "is_start", False)),
            }
            logger.info("callback AGENT_CALL raw=%r", event)
            logger.info("callback AGENT_CALL dump=%s", dump_event(event))
            logger.info("callback AGENT_CALL payload=%s", payload)
            await self._emit(AgentEventType.AGENT_CALL.value, payload)

        @self.client.on(self.event_type.AGENT)
        async def on_agent_text(event: Any) -> None:
            payload = {"content": safe_get(event, "content", "")}
            logger.info("callback AGENT raw=%r", event)
            logger.info("callback AGENT dump=%s", dump_event(event))
            logger.info("callback AGENT payload=%s", payload)
            await self._emit(AgentEventType.AGENT_TEXT.value, payload)

        @self.client.on(self.event_type.TOOL_EXECUTION)
        async def on_tool(event: Any) -> None:
            payload = {
                "tool_name": safe_get(event, "tool_name", "unknown"),
                "is_start": bool(safe_get(event, "is_start", False)),
                "result_summary": safe_get(event, "result_summary", None),
            }
            logger.info("callback TOOL_EXECUTION raw=%r", event)
            logger.info("callback TOOL_EXECUTION dump=%s", dump_event(event))
            logger.info("callback TOOL_EXECUTION payload=%s", payload)
            await self._emit("tool", payload)

        self._registered = True
        logger.info("RelayClient 事件处理器注册完成")

    async def relay_worker(self) -> None:
        try:
            logger.info("relay_worker 启动")
            await self._emit("debug", {"step": "connecting", "ws_url": self.ws_url})

            async with self.client:
                logger.info("ws 已连接: %s", self.ws_url)
                await self._emit("debug", {"step": "connected"})

                if self.project_home:
                    config_payload = {"project_home": self.project_home}
                    logger.info("准备发送配置: %s", config_payload)
                    await self.client.send_config(config_payload)
                    logger.info("send_config 完成")
                    await self._emit(
                        "debug",
                        {
                            "step": "config_sent",
                            "project_home": self.project_home,
                        },
                    )

                logger.info("准备发送消息: %s", self.message)
                await self.client.send_message(self.message)
                logger.info("send_message 完成")
                await self._emit(
                    "debug",
                    {
                        "step": "message_sent",
                        "message": self.message,
                    },
                )

                logger.info("开始等待 wait_until_done, timeout=%ss", self.timeout_seconds)
                await asyncio.wait_for(self.client.wait_until_done(), timeout=self.timeout_seconds)
                logger.info("wait_until_done 已完成")

                await self._emit("done", {"status": "completed"})

        except asyncio.TimeoutError:
            logger.exception("wait_until_done 超时, timeout=%ss", self.timeout_seconds)
            await self._emit(
                "error",
                {
                    "message": f"wait_until_done timeout after {self.timeout_seconds}s",
                },
            )
            await self._emit("done", {"status": "timeout"})

        except Exception:
            logger.exception("relay_worker 异常")
            await self._emit("error", {"message": "relay_worker exception"})
            await self._emit("done", {"status": "error"})

        finally:
            logger.info("relay_worker 结束")

    async def stream(self, request: Request) -> AsyncGenerator[str, None]:
        logger.info("stream 启动")
        worker_task = asyncio.create_task(self.relay_worker())

        try:
            ready_payload = {"status": "ready"}
            logger.info("先返回 ready: %s", ready_payload)
            yield format_sse(ready_payload, event="ready")

            while True:
                if await request.is_disconnected():
                    logger.info("客户端已断开连接")
                    worker_task.cancel()
                    break

                try:
                    event, data = await asyncio.wait_for(self.queue.get(), timeout=15)
                    logger.info("从 queue 取到消息: event=%s data=%s", event, data)

                    sse_chunk = format_sse(data, event=event)
                    logger.info("SSE 输出 event=%s", event)
                    yield sse_chunk

                    if event == "done":
                        logger.info("收到 done, 结束 SSE")
                        break

                except asyncio.TimeoutError:
                    logger.info("15 秒没有新消息, 发送 SSE 心跳 ping")
                    yield ": ping\n\n"

        finally:
            logger.info("准备结束 stream, 取消 worker_task")
            worker_task.cancel()
            with suppress(asyncio.CancelledError):
                await worker_task
            logger.info("stream 结束")
