from __future__ import annotations

"""Compatibility exports for the initial Phase-2A prototype."""

from .model_client import ModelBackend
from .models import InferenceMetadata, InferenceRequest, InferenceResponse, TokenUsage

InferenceResult = InferenceResponse

__all__ = [
    "InferenceMetadata",
    "InferenceRequest",
    "InferenceResponse",
    "InferenceResult",
    "ModelBackend",
    "TokenUsage",
]
