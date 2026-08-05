from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE1_ROOT = PROJECT_ROOT / "runtime" / "phase1-runtime"
if str(PHASE1_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE1_ROOT))

from backend.config import BackendSettings  # noqa: E402
from backend.factory import create_backend  # noqa: E402
from backend.model_client import ModelBackend, ModelClient  # noqa: E402
from runtime.agent_runtime import Agent  # noqa: E402
from runtime.config import RuntimeConfig  # noqa: E402
from runtime.ledger import LedgerStub  # noqa: E402
from runtime.sandbox import Sandbox  # noqa: E402
from runtime.tools import ToolRegistry  # noqa: E402


def build_agent(
    config: RuntimeConfig | None = None,
    backend: ModelBackend | None = None,
) -> tuple[Agent, LedgerStub, RuntimeConfig]:
    runtime_config = config or RuntimeConfig.default()
    ledger = LedgerStub(runtime_config.trajectory_root)
    sandbox = Sandbox(runtime_config.project_root, runtime_config.sandbox_root)
    tools = ToolRegistry(sandbox, ledger)
    settings = BackendSettings.from_environment(
        default_base_url=runtime_config.api_base_url,
        default_model_name=runtime_config.model_name,
        default_timeout_seconds=runtime_config.request_timeout_seconds,
    )
    selected_backend = backend or create_backend(settings)
    model = ModelClient(selected_backend)
    return Agent(model, tools, ledger), ledger, runtime_config
