from __future__ import annotations

from .model_client import ModelBackend, ModelClient


class Phase1ModelClientBridge(ModelClient):
    """Compatibility name for ModelClient's frozen Phase-1 chat surface."""

    def __init__(self, backend: ModelBackend) -> None:
        super().__init__(backend)
