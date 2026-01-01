"""Compatibility layer for optional Pydantic usage."""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Dict

try:
    from pydantic import BaseModel, Field, field_validator  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal environments

    def Field(default: Any = None, default_factory: Callable[[], Any] | None = None) -> Any:
        if default_factory is not None:
            return default_factory()
        return default

    def field_validator(*_args: Any, **_kwargs: Any):  # type: ignore[override]
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return func

        return decorator

    class BaseModel:
        def __init__(self, **data: Any) -> None:
            for key, value in data.items():
                setattr(self, key, value)
            for key, value in self.__class__.__dict__.items():
                if key.startswith("_") or callable(value):
                    continue
                if not hasattr(self, key):
                    setattr(self, key, value)

        def model_dump(self) -> Dict[str, Any]:
            return _dump_value(self.__dict__)


def _dump_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [_dump_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _dump_value(item) for key, item in value.items()}
    return value
