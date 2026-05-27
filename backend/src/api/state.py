"""In-memory app state for the API server."""

from __future__ import annotations


class ApiSessionState:
    def get(self, key: str, default=None):
        return _STORE.get(key, default)

    def __setitem__(self, key: str, value) -> None:
        _STORE[key] = value

    def pop(self, key: str, default=None):
        return _STORE.pop(key, default)


_STORE: dict = {}
session = ApiSessionState()


def clear_analysis_keys() -> None:
    for key in ("pipeline_result", "chat_context", "analysis_signature"):
        _STORE.pop(key, None)
