from __future__ import annotations

from typing import Any, Mapping


SEMANTIC_AUTHORITY_SCHEMA = "uaea.semantic_authority.v0"
INTERPRETATION = "interpretation"
EXECUTION_CONSTRAINT = "execution_constraint"
USER_DIRECTIVE_BASIS = "existing_web_user_directive"


def _supported_key(key: Any) -> bool:
    return isinstance(key, str) and (
        key in {"web.provider", "web.fallback"} or key.startswith("web.exclude_provider:")
    )


def user_directive_basis(
    provenance: Mapping[str, Any], *, key: str, value: str,
) -> dict[str, str]:
    """Reference an existing user-input contract, not an inferred Goal or permission."""
    if provenance.get("source_event_type") != "USER_INPUT" or not provenance.get("input_id"):
        raise ValueError("User directive requires user-input provenance")
    if not _supported_key(key):
        raise ValueError("Directive is outside the existing Web contract")
    return {"type": USER_DIRECTIVE_BASIS, "input_id": str(provenance["input_id"]),
            "key": key, "value": value}


def has_execution_authority(metadata: Mapping[str, Any]) -> bool:
    basis = metadata.get("promotion_basis")
    provenance = metadata.get("provenance")
    if not isinstance(basis, Mapping) or not isinstance(provenance, Mapping):
        return False
    return (
        metadata.get("kind") == "capability_constraint"
        and _supported_key(metadata.get("key"))
        and metadata.get("authority_level") == EXECUTION_CONSTRAINT
        and basis.get("type") == USER_DIRECTIVE_BASIS
        and provenance.get("source_event_type") == "USER_INPUT"
        and bool(provenance.get("input_id"))
        and basis.get("input_id") == provenance.get("input_id")
        and basis.get("key") == metadata.get("key")
        and basis.get("value") == metadata.get("value")
    )


def authority_level(metadata: Mapping[str, Any]) -> str:
    return EXECUTION_CONSTRAINT if has_execution_authority(metadata) else INTERPRETATION
