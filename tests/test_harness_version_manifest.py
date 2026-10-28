from __future__ import annotations

import os
import io
import hashlib
import tempfile
import tomllib
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

from harness.version_manifest import codex_process_environment, identify_harness, load_manifest, selected_harness, verify_binary_digest


class HarnessVersionManifestTests(unittest.TestCase):
    def setUp(self):
        # This suite compares the two retained x86 versions; ARM availability is checked separately.
        host = patch("harness.version_manifest.current_platform", return_value="linux-x86_64")
        host.start()
        self.addCleanup(host.stop)

    def test_exact_pinned_commits_are_distinct(self):
        self.assertEqual(selected_harness("rust-v0.154.0")["commit"],
                         "6b9826e3aa83b1a5947db50f4332cb9c65f1b340")
        self.assertEqual(selected_harness("rust-v0.163.0")["commit"],
                         "83086188ae0614bd882818ff1aa23f3194962012")

    def test_explicit_and_environment_override_do_not_rewrite_manifest(self):
        before = load_manifest()
        with patch.dict(os.environ, {"UAEA_CODEX_VERSION": "rust-v0.163.0"}):
            self.assertEqual(selected_harness()["tag"], "rust-v0.163.0")
            self.assertEqual(selected_harness("rust-v0.154.0")["tag"], "rust-v0.154.0")
        self.assertEqual(load_manifest(), before)

    def test_default_comes_from_manifest(self):
        with patch.dict(os.environ, {"UAEA_CODEX_VERSION": ""}):
            self.assertEqual(selected_harness()["tag"], load_manifest()["active_version"])

    def test_unknown_tag_fails_without_fallback(self):
        with self.assertRaises(ValueError):
            selected_harness("rust-v0.unknown")

    def test_binaries_and_sources_are_isolated(self):
        old, new = (selected_harness(tag) for tag in ("rust-v0.154.0", "rust-v0.163.0"))
        self.assertNotEqual(old["binary"], new["binary"])
        self.assertNotEqual(old["source_location"], new["source_location"])
        self.assertEqual(identify_harness(Path(old["binary"]))["commit"], old["commit"])
        scripts = Path(__file__).resolve().parents[1] / "scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        from h3_context_characterization import DEFAULT_CODEX_HOME_ROOT, DEFAULT_WORKSPACE_ROOT
        self.assertEqual(DEFAULT_CODEX_HOME_ROOT.name, selected_harness()["tag"])
        self.assertEqual(DEFAULT_WORKSPACE_ROOT.name, selected_harness()["tag"])

    def test_unknown_override_does_not_claim_a_pinned_commit(self):
        self.assertEqual(identify_harness(Path("/tmp/user-provided-codex"))["commit"], "unknown")

    def test_version_probe_and_runtime_environment_do_not_forward_credentials(self):
        with patch.dict(os.environ, {"SERPAPI_KEY": "test-only-secret", "OPENAI_API_KEY": "test-only-secret"}):
            env = codex_process_environment(Path("/tmp/test-home"))
            self.assertNotIn("SERPAPI_KEY", env)
            self.assertNotIn("OPENAI_API_KEY", env)
            self.assertEqual(env["CODEX_HOME"], str(Path("/tmp/test-home")))
            self.assertEqual(os.environ["SERPAPI_KEY"], "test-only-secret")

    def test_binary_digest_is_checked_not_inferred_from_its_filename(self):
        record = {"binary_sha256": hashlib.sha256(b"known executable").hexdigest()}
        with patch.object(Path, "open", return_value=io.BytesIO(b"known executable")):
            verify_binary_digest(Path("unused"), record)
        self.assertTrue(record["binary_digest_verified"])
        with patch.object(Path, "open", return_value=io.BytesIO(b"different executable")):
            with self.assertRaises(RuntimeError):
                verify_binary_digest(Path("unused"), record)

    def test_generated_config_omits_ignored_root_keys_without_relaxing_runtime(self):
        scripts = Path(__file__).resolve().parents[1] / "scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        from h3_context_characterization import write_config
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            write_config(home, "http://127.0.0.1:8002", 32768)
            config = tomllib.loads((home / "config.toml").read_text())
        self.assertNotIn("skip_host_skill_discovery", config)
        self.assertNotIn("disable_response_storage", config)
        self.assertEqual(config["model_context_window"], 32768)
        self.assertFalse(config["features"]["shell_tool"])
        self.assertFalse(config["features"]["unified_exec"])
        self.assertFalse(config["model_providers"]["uaea_local_vllm"]["requires_openai_auth"])
        from h3_app_server_lifecycle_probe import classify_native_file_turn
        self.assertNotEqual(classify_native_file_turn({
            "agent_texts": ["# UAEA"], "command_items": [
                {"status": "completed", "exitCode": 1, "aggregatedOutput": "# UAEA"}],
        }), "PASS_VIA_HARNESS_COMMAND")
        self.assertEqual(classify_native_file_turn({
            "agent_texts": ["UAEA"], "command_items": [
                {"status": "completed", "exitCode": 0, "aggregatedOutput": "# UAEA"}],
        }), "PASS_VIA_HARNESS_COMMAND")
