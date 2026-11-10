"""Opt-in capacity experiment must preserve formal defaults and service health gates."""
import json
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch
import contextlib
import io
import memory.sqlite_store

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import h3_harness_interactive_repl as repl
import h3_context_characterization as context


class Context64ExperimentTests(unittest.TestCase):
    def test_default_stays_32k_and_expansion_requires_explicit_opt_in(self):
        self.assertEqual(repl.parse_args(["--profile", "n1x"]).context, 32768)
        for flags in (["--context", "65536"],
                      ["--experimental-context-64k"],
                      ["--context", "65536", "--experimental-context-64k", "--vllm-mode", "managed"]):
            with self.subTest(flags=flags), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    repl.parse_args(["--profile", "n1x", *flags])
        args = repl.parse_args(["--profile", "n1x", "--context", "65536",
            "--experimental-context-64k", "--base-url", "http://127.0.0.1:8003",
            "--model", "nemotron-bolt-n1x"])
        self.assertEqual(args.context, 65536)
        self.assertEqual(args.vllm_mode, "external")

    def test_capacity_configuration_preserves_reserve_fraction_and_32k_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            for size, limit in ((32768, 24576), (65536, 49152)):
                home = Path(tmp) / str(size)
                context.write_config(home, "http://127.0.0.1:8003", size,
                                     model="nemotron-bolt-n1x", n1x=True)
                cfg = tomllib.loads((home / "config.toml").read_text())
                self.assertEqual(cfg["model_context_window"], size)
                self.assertEqual(cfg["model_auto_compact_token_limit"], limit)
                self.assertFalse(cfg["features"]["shell_tool"])
                self.assertEqual(cfg["web_search"], "disabled")

    def test_64k_harness_must_reject_an_actual_32k_service(self):
        response = io.StringIO(json.dumps({"data": [
            {"id": "nemotron-bolt-n1x", "max_model_len": 32768}]}))
        with patch.object(context.urllib.request, "urlopen", return_value=response):
            with self.assertRaises(RuntimeError):
                context.wait_for_external_health("http://127.0.0.1:8003",
                                                "nemotron-bolt-n1x", 65536, 2)


if __name__ == "__main__":
    unittest.main()
