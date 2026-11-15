"""Opt-in research receipt budget, reusing the existing read-only tool."""
import json
from dataclasses import replace
from research.goal_sideband import ProposalAdapter
from runtime.capability import ToolResult


def _guard_section_index(registry):
    """Opt in on this research-owned registry, including its existing Host path.

    Dynamic-tool schemas are descriptive and Native can drop numeric bounds.
    Do not rely on minimum=1 or let Phase-1 coerce an invalid index to None.
    The immutable Phase-1 handler and all non-section capabilities are unchanged.
    """
    execute = registry.execute_capability
    if getattr(execute, "_research_section_index_guard", False):
        return

    def guarded(capability, arguments, objective):
        if capability == "document.read_section":
            index = arguments.get("section_index")
            if type(index) is not int or index < 1:
                return ToolResult(False, "section_index must be an integer >= 1; 0 is not a directory selector.", {
                    "capability": capability,
                    "tool": "read_section",
                    "execution_status": "validation_failed",
                    "execution_succeeded": False,
                    "result_available": False,
                    "failure_stage": "argument_validation",
                    "error_kind": "parameter_validation",
                    "error_code": "invalid_section_index",
                    "requested_section_index": index,
                    "retryable": True,
                    "retry_instruction": (
                        "Use an integer section_index >= 1 from the actual returned section_catalog. "
                        "Do not use 0 or assume a zero-based index. Directory/root numbering must match "
                        "the advertised source; no source body has been read by this rejected attempt."
                    ),
                    "source_body_read": False,
                })
        return execute(capability, arguments, objective)

    guarded._research_section_index_guard = True
    registry.execute_capability = guarded



class ResearchDocumentAdapter(ProposalAdapter):
    def __init__(self, registry, bindings, *, catalogue_ordinals=(2,), **kwargs):
        # SharedExecutionHost calls the same registry. Returning a real failed
        # ToolResult here lets its ordinary Step/Observation/journal path record
        # rejection; no fabricated Native receipt or hidden 0 -> 1 rewrite.
        if any(type(index) is not int or index < 1 for index in catalogue_ordinals):
            raise ValueError("Research catalogue ordinals must be positive integers")
        # Application-owned fixture contract: generated root=1, directory=2.
        # This is not inferred from source prose or supplied by a model.
        self.catalogue_ordinals = frozenset(catalogue_ordinals)
        _guard_section_index(registry)
        super().__init__(registry, bindings, **kwargs)

    def dispatch(self, *args, **kwargs):
        result = super().dispatch(*args, **kwargs)
        data = result.tool_result.data
        if (not result.ok or result.observation.capability != "document.read_section"
                or data.get("section_index", 0) <= 1
                or data.get("section_index") in self.catalogue_ordinals
                or not isinstance(data.get("content"), str)):
            return result
        maximum = result.max_output_chars
        def complete(budget):
            candidate = replace(result, max_output_chars=budget)
            try:
                value = json.loads(candidate.to_app_server_response()["contentItems"][0]["text"])
            except ValueError:
                return False
            projection = value["data"].get("document_projection")
            return (projection.get("content_complete") is True if projection else
                    value["data"].get("content") == data["content"])
        if not complete(maximum):
            return result
        # Reduce redundant directory metadata, never the selected body. No tool is
        # re-executed: these are pure receipt serializations under the same cap.
        low, high = 1, maximum
        while low < high:
            mid = (low + high) // 2
            if complete(mid):
                high = mid
            else:
                low = mid + 1
        return replace(result, max_output_chars=low)
