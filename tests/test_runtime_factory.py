from __future__ import annotations

import unittest

from backend.lmf_backend import LMFBackend
from backend.model_client import ModelClient
from phase2.runtime_factory import build_agent


class RuntimeFactoryTests(unittest.TestCase):
    def test_frozen_agent_receives_phase2a_model_client(self):
        agent, ledger, config = build_agent()

        self.assertIsInstance(agent.model, ModelClient)
        self.assertIsInstance(agent.model.backend, LMFBackend)
        self.assertEqual(agent.model.backend.base_url, config.api_base_url)
        self.assertEqual(agent.model.backend.model_name, config.model_name)
        self.assertTrue(str(ledger.path).startswith(str(config.trajectory_root)))


if __name__ == "__main__":
    unittest.main()
