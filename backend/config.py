from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_BACKEND_URLS = {
    "lmf": "http://127.0.0.1:8000/v1",
    "vllm": "http://127.0.0.1:8001/v1",
}


@dataclass(frozen=True)
class BackendSettings:
    name: str
    base_url: str
    model_name: str
    timeout_seconds: int = 300
    api_key: str = "uaea-local"

    @classmethod
    def from_environment(
        cls,
        default_base_url: str,
        default_model_name: str,
        default_timeout_seconds: int,
    ) -> "BackendSettings":
        name = os.environ.get("UAEA_BACKEND", "lmf").strip().lower()
        fallback_urls = {**DEFAULT_BACKEND_URLS, "lmf": default_base_url}
        fallback_url = fallback_urls.get(name, default_base_url)
        return cls(
            name=name,
            base_url=os.environ.get("UAEA_BACKEND_BASE_URL", fallback_url).rstrip("/"),
            model_name=os.environ.get("UAEA_BACKEND_MODEL", default_model_name),
            timeout_seconds=int(os.environ.get("UAEA_BACKEND_TIMEOUT", default_timeout_seconds)),
            api_key=os.environ.get("UAEA_BACKEND_API_KEY", "uaea-local"),
        )
