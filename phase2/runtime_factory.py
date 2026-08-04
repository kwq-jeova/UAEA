from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE1_ROOT = PROJECT_ROOT / "runtime" / "phase1-runtime"
if str(PHASE1_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE1_ROOT))

from backend.lmf_backend import LMFBackend  # noqa: E402
from backend.model_client import ModelClient  # noqa: E402
from runtime.agent_runtime import Agent  # noqa: E402
from runtime.config import RuntimeConfig  # noqa: E402
from runtime.ledger import LedgerStub  # noqa: E402
from runtime.sandbox import Sandbox  # noqa: E402
from runtime.tools import ToolRegistry  # noqa: E402


def build_agent(config: RuntimeConfig | None = None) -> tuple[Agent, LedgerStub, RuntimeConfig]:
    runtime_config = config or RuntimeConfig.default()
    ledger = LedgerStub(runtime_config.trajectory_root)
    sandbox = Sandbox(runtime_config.project_root, runtime_config.sandbox_root)
    tools = ToolRegistry(sandbox, ledger)
    backend = LMFBackend(
        base_url=runtime_config.api_base_url,
        model_name=runtime_config.model_name,
        timeout_seconds=runtime_config.request_timeout_seconds,
    )
    model = ModelClient(backend)
    return Agent(model, tools, ledger), ledger, runtime_config
