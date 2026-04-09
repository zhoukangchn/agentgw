from __future__ import annotations

from importlib import import_module
from typing import Any


def load_relay_sdk_client(
    ws_url: str,
    *,
    module_path: str = "your_sdk",
    client_class_name: str = "RelayClient",
) -> Any:
    module = import_module(module_path)
    client_class = getattr(module, client_class_name)
    return client_class(ws_url)


def load_relay_sdk_event_type(
    *,
    module_path: str = "your_sdk",
    enum_name: str = "EventType",
) -> Any:
    module = import_module(module_path)
    return getattr(module, enum_name)
