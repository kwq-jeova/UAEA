from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import tomllib
from unittest import TestCase
from unittest.mock import Mock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import h3_harness_interactive_repl as repl
import h3_context_characterization as context
from harness.version_manifest import identify_harness, load_manifest, selected_harness, verify_binary_digest


class N1XHarnessStartupTests(TestCase):
    def test_platform_selection_preserves_x86_records_and_identifies_arm_binary(self):
        manifest = load_manifest()
        original = manifest["versions"]["rust-v0.163.0"]
        with patch("harness.version_manifest.current_platform", return_value="linux-x86_64"):
            x86 = selected_harness("rust-v0.163.0")
        with patch("harness.version_manifest.current_platform", return_value="linux-aarch64"):
            arm = selected_harness("rust-v0.163.0")
        self.assertEqual(x86["binary"], original["binary"])
        self.assertEqual(x86["binary_sha256"], original["binary_sha256"])
        self.assertEqual(arm["commit"], x86["commit"])
        self.assertEqual(arm["build_target"], "aarch64-unknown-linux-gnu")
        self.assertEqual(identify_harness(Path(arm["binary"]))["commit"], arm["commit"])

    def test_bundled_bwrap_digest_mismatch_is_rejected(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "codex"
            binary.write_bytes(b"codex")
            (binary.parent / "codex-resources").mkdir()
            (binary.parent / "codex-resources" / "bwrap").write_bytes(b"unexpected")
            with self.assertRaisesRegex(RuntimeError, "bwrap checksum"):
                verify_binary_digest(binary, {
                    "binary_sha256": hashlib.sha256(b"codex").hexdigest(),
                    "bwrap_sha256": hashlib.sha256(b"expected").hexdigest(),
                })

    def test_n1x_profile_and_legacy_h3_defaults(self):
        n1x = repl.parse_args(["--profile", "n1x"])
        self.assertEqual((n1x.context, n1x.base_url, n1x.vllm_mode),
                         (32768, "http://127.0.0.1:8000", "external"))
        self.assertEqual(n1x.model, "Qwen2.5-14B-Instruct-AWQ")
        self.assertNotIn("/mnt/", str(n1x.result_root))
        with patch("harness.version_manifest.current_platform", return_value="linux-x86_64"):
            h3 = repl.parse_args(["--profile", "h3"])
            self.assertEqual(h3.codex_bin, Path(load_manifest()["versions"]["rust-v0.163.0"]["binary"]))
        self.assertEqual((h3.context, h3.base_url, h3.vllm_mode),
                         (32768, "http://127.0.0.1:8002", "managed"))
        self.assertEqual(h3.model, context.DEFAULT_MODEL)

    def test_n1x_rejects_managed_or_frozen_endpoint(self):
        for flags in (["--vllm-mode", "managed"], ["--context", "8192"],
                      ["--base-url", "http://127.0.0.1:8001"],
                      ["--generation-diagnostics"]):
            with self.subTest(flags=flags), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    repl.parse_args(["--profile", "n1x", *flags])

    def test_external_health_rejects_wrong_model_and_oversized_context(self):
        for data in ({"data": [{"id": "wrong"}]},
                     {"data": [{"id": "actual", "max_model_len": 8192}]}):
            with self.subTest(data=data):
                response = io.StringIO(json.dumps(data))
                with patch.object(context.urllib.request, "urlopen", return_value=response):
                    with self.assertRaises(RuntimeError):
                        context.wait_for_external_health("http://127.0.0.1:8000", "actual", 32768, 2)

    def test_external_exit_and_failure_never_start_or_stop_service(self):
        for fail in (False, True):
            with self.subTest(fail=fail), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                args = repl.parse_args(["--profile", "n1x", "--result-root", str(root / "results"),
                                       "--codex-home-root", str(root / "home"),
                                       "--workspace-root", str(root / "workspace")])
                app = Mock()
                if fail:
                    app.start.side_effect = RuntimeError("initialize failed")
                with patch.object(repl, "load_web_environment"), \
                     patch.object(repl, "wait_for_external_health", return_value=0.1), \
                     patch.object(repl, "start_vllm") as start, \
                     patch.object(repl, "stop_process") as stop, \
                     patch.object(repl, "build_interactive_adapter", return_value=Mock()), \
                     patch.object(repl, "InteractiveAppServer", return_value=app), \
                     patch.object(repl, "read_user_input", return_value="exit"), \
                     contextlib.redirect_stdout(io.StringIO()):
                    if fail:
                        with self.assertRaises(RuntimeError):
                            repl.run(args)
                    else:
                        self.assertEqual(repl.run(args), 0)
                    start.assert_not_called()
                    stop.assert_not_called()
                    app.close.assert_called_once()
                config = next((root / "home").glob("*/config.toml"))
                config = tomllib.loads(config.read_text())
                self.assertEqual(config["model"], args.model)
                self.assertEqual(config["model_context_window"], 32768)

    def test_n1x_disables_out_of_scope_native_tools_without_changing_h3_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            context.write_config(home, "http://127.0.0.1:8000", 32768,
                                 model="Qwen2.5-14B-Instruct-AWQ", n1x=True)
            n1x = tomllib.loads((home / "config.toml").read_text())
            self.assertEqual(n1x["web_search"], "disabled")
            for key in ("multi_agent", "multi_agent_v2", "goals", "memories", "view_image"):
                self.assertFalse(n1x["features"][key])
            context.write_config(home, "http://127.0.0.1:8002", 32768)
            h3 = tomllib.loads((home / "config.toml").read_text())
            self.assertNotIn("web_search", h3)
            self.assertNotIn("multi_agent", h3["features"])
            self.assertNotIn("goals", h3["features"])

    def test_wrong_platform_profiles_are_rejected(self):
        for host, profile in [("linux-x86_64", "n1x"), ("linux-aarch64", "h3")]:
            with self.subTest(host=host), patch("harness.version_manifest.current_platform", return_value=host), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    repl.parse_args(["--profile", profile])

    def test_missing_arm_version_never_falls_back_to_x86(self):
        with patch("harness.version_manifest.current_platform", return_value="linux-aarch64"):
            with self.assertRaisesRegex(ValueError, "no fallback"):
                selected_harness("rust-v0.154.0")

    def test_elf_architecture_guard_includes_explicit_binary_overrides(self):
        from harness.version_manifest import verify_binary_platform
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "codex"
            for machine, host in [(183, "linux-aarch64"), (62, "linux-x86_64")]:
                header = bytearray(20)
                header[:6] = bytes((127, 69, 76, 70, 2, 1))
                header[18:20] = machine.to_bytes(2, "little")
                binary.write_bytes(header)
                with patch("harness.version_manifest.current_platform", return_value=host):
                    record = {"tag": "explicit_binary_override"}
                    verify_binary_platform(binary, record)
                    self.assertTrue(record["binary_platform_verified"])
                other = "linux-x86_64" if host == "linux-aarch64" else "linux-aarch64"
                with patch("harness.version_manifest.current_platform", return_value=other):
                    with self.assertRaisesRegex(RuntimeError, "native 64-bit ELF"):
                        verify_binary_platform(binary, {"tag": "explicit_binary_override"})

    def test_registered_binary_override_cannot_cross_platforms(self):
        manifest = load_manifest()["versions"]["rust-v0.163.0"]
        for host, profile, binary in [
            ("linux-x86_64", "h3", manifest["platforms"]["linux-aarch64"]["binary"]),
            ("linux-aarch64", "n1x", manifest["binary"]),
        ]:
            with self.subTest(host=host), patch("harness.version_manifest.current_platform", return_value=host), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    repl.parse_args(["--profile", profile, "--codex-bin", binary])
