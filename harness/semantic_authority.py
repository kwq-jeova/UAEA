from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SEMANTIC_AUTHORITY_SCHEMA = "uaea.semantic_authority.v0"
INTERPRETATION = "interpretation"
EXECUTION_CONSTRAINT = "execution_constraint"
USER_DIRECTIVE_BASIS = "existing_web_user_directive"
SHARED_BINDING_FIELDS = ("kind", "owner", "scope", "strength", "authority_level", "provenance")
SHARED_BASIS_FIELDS = ("type", "input_id")


def compact_semantic_bindings(
    bindings: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Share identical source metadata; keep each constraint's basis key/value."""
    if len(bindings) < 2:
        return bindings, {}
    shared = {
        key: bindings[0][key] for key in SHARED_BINDING_FIELDS
        if key in bindings[0] and all(key in item and item[key] == bindings[0][key]
                                     for item in bindings)
    }
    compact = [{key: deepcopy(value) for key, value in item.items() if key not in shared}
               for item in bindings]
    bases = [item.get("promotion_basis") for item in bindings]
    if all(isinstance(basis, Mapping) for basis in bases):
        defaults = {key: bases[0][key] for key in SHARED_BASIS_FIELDS
                    if key in bases[0] and all(basis.get(key) == bases[0][key] for basis in bases)}
        if defaults:
            shared["promotion_basis_defaults"] = defaults
            for item in compact:
                item["promotion_basis"] = {key: value for key, value in item["promotion_basis"].items()
                                           if key not in defaults}
    return compact, shared


def expand_semantic_binding(
    binding: Mapping[str, Any], shared: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Expand transport metadata before applying the unchanged authority predicate."""
    if shared is None:
        shared = {}
    if not isinstance(shared, Mapping) or any(
            key not in (*SHARED_BINDING_FIELDS, "promotion_basis_defaults") for key in shared):
        return {}
    defaults = shared.get("promotion_basis_defaults", {})
    if not isinstance(defaults, Mapping) or any(key not in SHARED_BASIS_FIELDS for key in defaults):
        return {}
    expanded = {**{key: value for key, value in shared.items() if key in SHARED_BINDING_FIELDS}, **binding}
    basis = binding.get("promotion_basis")
    if isinstance(basis, Mapping):
        expanded["promotion_basis"] = {**defaults, **basis}
    return expanded


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
