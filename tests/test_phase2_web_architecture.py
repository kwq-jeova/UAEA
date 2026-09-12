from __future__ import annotations

import ast
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE2_ROOT = PROJECT_ROOT / "phase2"


def _module_ast(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imported_modules(path: Path) -> set[str]:
    tree = _module_ast(path)
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            modules.add(module)
    return modules


def _source_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class Phase2WebArchitectureTests(unittest.TestCase):
    def test_web_runtime_entry_reuses_runtime_factory(self):
        source = _source_text(PHASE2_ROOT / "web_repl.py")

        self.assertIn("from .runtime_factory import build_agent", source)
        self.assertIn("agent, ledger, config = build_agent()", source)
        self.assertIn("Phase2WebShell(", source)

    def test_web_modules_do_not_create_model_or_backend_clients(self):
        forbidden_imports = {
            "backend.model_client",
            "backend.vllm_backend",
            "backend.lmf_backend",
            "backend.factory",
            ".runtime_factory",
        }
        checked_modules = [
            PHASE2_ROOT / "web_adapter.py",
            PHASE2_ROOT / "web_capability.py",
            PHASE2_ROOT / "web_context.py",
            PHASE2_ROOT / "web_shell.py",
            PHASE2_ROOT / "web_intent.py",
        ]

        for path in checked_modules:
            imports = _imported_modules(path)
            self.assertTrue(
                imports.isdisjoint(forbidden_imports),
                f"{path.name} imports backend/runtime factory: {imports}",
            )

    def test_web_modules_do_not_call_chat_completion_directly(self):
        checked_modules = [
            PHASE2_ROOT / "web_adapter.py",
            PHASE2_ROOT / "web_capability.py",
            PHASE2_ROOT / "web_context.py",
            PHASE2_ROOT / "web_shell.py",
            PHASE2_ROOT / "web_repl.py",
            PHASE2_ROOT / "web_intent.py",
        ]

        for path in checked_modules:
            source = _source_text(path)
            self.assertNotIn("/chat/completions", source)
            self.assertNotIn("InferenceRequest", source)
            self.assertNotIn(".generate(", source)

    def test_semantic_web_intent_uses_chat_surface_only(self):
        source = _source_text(PHASE2_ROOT / "web_intent.py")

        self.assertIn("def chat(", source)
        self.assertIn("model.chat(", source)
        self.assertNotIn("ModelClient", source)
        self.assertNotIn("VLLMBackend", source)
        self.assertNotIn("create_backend", source)


if __name__ == "__main__":
    unittest.main()
