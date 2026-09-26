from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import h3_harness_interactive_repl as interactive_repl  # noqa: E402


class H3InteractiveWebSchemaTests(unittest.TestCase):
    def test_interactive_dynamic_schema_preserves_web_constraints(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            specs = interactive_repl.build_interactive_adapter(Path(tmpdir)).dynamic_tools()

        web_search = next(spec for spec in specs if spec["name"] == "web_search")
        properties = web_search["inputSchema"]["properties"]
        self.assertEqual(
            {
                "query",
                "max_results",
                "provider",
                "allow_fallback",
                "language",
                "region",
                "exclude_domains",
                "preferred_domains",
                "source_types",
                "freshness",
            },
            set(properties),
        )
        self.assertEqual(
            properties["provider"]["enum"],
            ["google", "bing", "duckduckgo"],
        )
        self.assertEqual(
            properties["source_types"]["items"]["enum"],
            ["academic", "forum", "news", "documentation", "general"],
        )
        self.assertEqual(
            properties["freshness"]["enum"],
            ["day", "week", "month", "year", "recent", "any"],
        )
        self.assertIn("Only cite URLs returned", web_search["description"])
        self.assertEqual(web_search["inputSchema"]["additionalProperties"], False)

    def test_runtime_facts_describe_search_and_fetch_boundary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            specs = interactive_repl.build_interactive_adapter(Path(tmpdir)).dynamic_tools()
            context = interactive_repl.turn_context_payload(specs)

        web_limits = context["uaea.runtime_facts.web_limits"]["value"]
        self.assertIn("source discovery", web_limits)
        self.assertIn("page-level evidence", web_limits)
        self.assertIn("exclude_domains", web_limits)
        self.assertIn("best-effort", web_limits)
        self.assertIn("low_relevance", web_limits)
        self.assertIn("do not repeat the same query", web_limits)
        capability_state = json.loads(context["uaea.effective_capability_state"]["value"])
        self.assertTrue(capability_state["capabilities"]["web.search"]["available"])
        self.assertTrue(capability_state["capabilities"]["web.fetch"]["available"])
        self.assertEqual(
            capability_state["resolution"]["external_or_recent_public_information"],
            "web.search",
        )
        self.assertTrue(
            any("does not disable UAEA web.search" in rule for rule in capability_state["routing_rules"])
        )


if __name__ == "__main__":
    unittest.main()
