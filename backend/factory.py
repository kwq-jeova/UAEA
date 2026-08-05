from __future__ import annotations

from collections.abc import Callable

from .config import BackendSettings
from .lmf_backend import LMFBackend
from .model_client import ModelBackend
from .vllm_backend import VLLMBackend


BackendBuilder = Callable[[BackendSettings], ModelBackend]


def _build_lmf(settings: BackendSettings) -> ModelBackend:
    return LMFBackend(
        settings.base_url,
        settings.model_name,
        settings.timeout_seconds,
        settings.api_key,
    )


def _build_vllm(settings: BackendSettings) -> ModelBackend:
    return VLLMBackend(
        settings.base_url,
        settings.model_name,
        settings.timeout_seconds,
        settings.api_key,
    )


BACKEND_BUILDERS: dict[str, BackendBuilder] = {
    "lmf": _build_lmf,
    "vllm": _build_vllm,
}


def create_backend(settings: BackendSettings) -> ModelBackend:
    try:
        builder = BACKEND_BUILDERS[settings.name]
    except KeyError as exc:
        supported = ", ".join(sorted(BACKEND_BUILDERS))
        raise ValueError(f"Unsupported backend '{settings.name}'. Supported: {supported}.") from exc
    return builder(settings)
