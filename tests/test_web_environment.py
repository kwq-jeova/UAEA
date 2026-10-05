from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
from unittest.mock import Mock

from phase2 import web_environment as web_env

sys.path.insert(0, str(web_env.PROJECT_ROOT / "scripts"))
import h3_harness_interactive_repl as interactive_repl  # noqa: E402
import h3_context_characterization as context_probe  # noqa: E402


class WebEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "web.env"
        self.secret = "unit-test-not-a-real-credential"
        self.proxy = "http://127.0.0.1:7897"

    def write_env(self, content=None):
        if content is None:
            content = (
                f"SERPAPI_KEY='{self.secret}'\nHTTP_PROXY='{self.proxy}'\n"
                f"HTTPS_PROXY='{self.proxy}'\nhttp_proxy='{self.proxy}'\nhttps_proxy='{self.proxy}'\n"
            )
        self.path.write_text(content, encoding="utf-8")
        self.path.chmod(0o600)

    def test_private_file_loads_into_fresh_environment(self):
        self.write_env()
        target = {}
        status = web_env.load_web_environment(
            path=self.path, environ=target, require_key=True, require_proxy=True, report=False,
        )
        self.assertEqual(target["SERPAPI_KEY"], self.secret)
        for name in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
            self.assertEqual(target[name], self.proxy)
        self.assertEqual(status["SERPAPI_KEY"], "SET")
        self.assertEqual(target["NO_PROXY"], target["no_proxy"])
        self.assertTrue(set(web_env.LOOPBACK_HOSTS).issubset(target["no_proxy"].split(",")))

    def test_process_environment_has_precedence_and_aliases_are_unified(self):
        self.write_env()
        target = {"SERPAPI_KEY": "process-test-value", "https_proxy": "http://127.0.0.1:8888"}
        web_env.load_web_environment(path=self.path, environ=target, report=False)
        self.assertEqual(target["SERPAPI_KEY"], "process-test-value")
        self.assertEqual(target["HTTPS_PROXY"], target["https_proxy"])
        self.assertEqual(target["HTTPS_PROXY"], "http://127.0.0.1:8888")

    def test_existing_bypass_entries_are_preserved(self):
        self.write_env()
        target = {"NO_PROXY": "internal.example,localhost", "no_proxy": "other.example"}
        web_env.load_web_environment(path=self.path, environ=target, report=False)
        self.assertIn("internal.example", target["NO_PROXY"])
        self.assertIn("other.example", target["NO_PROXY"])
        self.assertEqual(target["NO_PROXY"].split(",").count("localhost"), 1)

    def test_missing_values_warn_without_disabling_existing_web(self):
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            status = web_env.load_web_environment(path=self.path, environ={})
        self.assertEqual(status["SERPAPI_KEY"], "MISSING")
        self.assertIn("WARNING", output.getvalue())

    def test_strict_validation_fails_before_mutating_environment(self):
        target = {}
        with self.assertRaises(web_env.WebEnvironmentError):
            web_env.load_web_environment(path=self.path, environ=target, require_key=True, report=False)
        self.assertEqual(target, {})
        self.write_env(f"SERPAPI_KEY='{self.secret}'\n")
        with self.assertRaises(web_env.WebEnvironmentError):
            web_env.load_web_environment(path=self.path, environ=target, require_proxy=True, report=False)
        self.assertEqual(target, {})

    @unittest.skipUnless(os.name == "posix", "POSIX ownership and mode")
    def test_permissions_fail_closed(self):
        self.write_env()
        self.path.chmod(0o644)
        with self.assertRaises(web_env.WebEnvironmentError):
            web_env.load_web_environment(path=self.path, environ={}, report=False)

    @unittest.skipUnless(os.name == "posix", "POSIX symlink check")
    def test_symlink_is_rejected(self):
        self.write_env()
        link = self.path.with_name("linked.env")
        link.symlink_to(self.path)
        with self.assertRaises(web_env.WebEnvironmentError):
            web_env.load_web_environment(path=link, environ={}, report=False)

    def test_repository_private_file_is_rejected(self):
        with self.assertRaises(web_env.WebEnvironmentError):
            web_env.load_web_environment(path=web_env.PROJECT_ROOT / "web.env", environ={}, report=False)

    def test_invalid_values_and_conflicts_never_echo_secrets(self):
        cases = (
            f"UNKNOWN='{self.secret}'\n",
            f"SERPAPI_KEY='{self.secret}'\nSERPAPI_KEY='{self.secret}'\n",
            f"SERPAPI_KEY='{self.secret}\n",
            f"HTTP_PROXY='socks5://{self.secret}:7897'\n",
            f"HTTP_PROXY='http://{self.secret}:7897'\nhttp_proxy='http://other:7897'\n",
        )
        for content in cases:
            with self.subTest(content_index=cases.index(content)):
                self.write_env(content)
                with self.assertRaises(web_env.WebEnvironmentError) as caught:
                    web_env.load_web_environment(path=self.path, environ={}, report=False)
                self.assertNotIn(self.secret, str(caught.exception))

    def test_shell_text_is_not_executed(self):
        self.write_env("export SERPAPI_KEY='$(touch should-not-exist)'\n")
        with self.assertRaises(web_env.WebEnvironmentError):
            web_env.load_web_environment(path=self.path, environ={}, report=False)
        self.assertFalse((Path(self.tmp.name) / "should-not-exist").exists())

    def test_status_reports_never_contain_key_or_proxy_credentials(self):
        self.write_env()
        target = {"HTTP_PROXY": "http://proxy-user:proxy-secret@127.0.0.1:7897"}
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            status = web_env.load_web_environment(path=self.path, environ=target)
        serialized = json.dumps(status) + output.getvalue()
        self.assertNotIn(self.secret, serialized)
        self.assertNotIn("proxy-secret", serialized)
        self.assertIn("SERPAPI_KEY=SET", serialized)

    def test_initializer_never_copies_key_or_overwrites_file(self):
        with patch.dict(os.environ, {"SERPAPI_KEY": self.secret, "HTTP_PROXY": self.proxy,
                                    "http_proxy": self.proxy, "HTTPS_PROXY": self.proxy,
                                    "https_proxy": self.proxy}, clear=True):
            web_env.initialize_private_env(self.path)
            original = self.path.read_bytes()
            self.assertNotIn(self.secret.encode(), original)
            self.assertEqual(web_env._read_private_env(self.path)["SERPAPI_KEY"], "")
            if os.name == "posix":
                self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(web_env.WebEnvironmentError):
                web_env.initialize_private_env(self.path)
            self.assertEqual(self.path.read_bytes(), original)

    def test_google_smoke_emits_only_bounded_confirmation(self):
        payload = {"search_metadata": {"status": "Success"}, "search_parameters": {"engine": "google"},
                   "organic_results": [{"title": "research", "link": "https://example.org"}]}
        response = io.BytesIO(json.dumps(payload).encode())
        with patch.dict(os.environ, {"SERPAPI_KEY": self.secret}), patch("urllib.request.build_opener") as opener:
            opener.return_value.open.return_value = response
            result = web_env.serpapi_environment_smoke()
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)["api_key"], [self.secret])
        self.assertEqual(result["reported_engine"], "google")
        self.assertEqual(result["organic_result_count"], 1)
        self.assertNotIn(self.secret, json.dumps(result))

    def test_google_smoke_http_error_does_not_echo_request_url_or_body(self):
        error = urllib.error.HTTPError("https://example.org/?api_key=" + self.secret, 401,
                                       self.secret, {}, io.BytesIO(self.secret.encode()))
        with patch.dict(os.environ, {"SERPAPI_KEY": self.secret}), patch("urllib.request.build_opener") as opener:
            opener.return_value.open.side_effect = error
            with self.assertRaises(web_env.WebEnvironmentError) as caught:
                web_env.serpapi_environment_smoke()
        self.assertIn("HTTP 401", str(caught.exception))
        self.assertNotIn(self.secret, str(caught.exception))

    def test_google_smoke_rejects_unconfirmed_or_empty_results(self):
        for payload in ({}, {"search_metadata": {"status": "Success"},
                             "search_parameters": {"engine": "bing"}, "organic_results": [{"link": "x"}]},
                        {"search_metadata": {"status": "Success"},
                         "search_parameters": {"engine": "google"}, "organic_results": []}):
            with patch.dict(os.environ, {"SERPAPI_KEY": self.secret}), patch("urllib.request.build_opener") as opener:
                opener.return_value.open.return_value = io.BytesIO(json.dumps(payload).encode())
                with self.assertRaises(web_env.WebEnvironmentError):
                    web_env.serpapi_environment_smoke()

    @unittest.skipUnless(os.name == "posix", "WSL/Bash startup")
    def test_fresh_shell_wrapper_loads_private_config_without_exports(self):
        self.write_env()
        environment = {name: value for name, value in os.environ.items() if name not in web_env.ENV_NAMES}
        environment["UAEA_WEB_ENV_FILE"] = str(self.path)
        result = subprocess.run(
            ["bash", "scripts/start_h3_harness_interactive.sh", "--web-env-check"],
            cwd=web_env.PROJECT_ROOT, env=environment, capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("HTTP_PROXY=SET", result.stderr)
        self.assertIn("HTTPS_PROXY=SET", result.stderr)
        self.assertIn("SERPAPI_KEY=SET", result.stderr)
        self.assertNotIn(self.secret, result.stdout + result.stderr)

    @unittest.skipUnless(os.name == "posix", "WSL/Bash startup")
    def test_fresh_shell_wrapper_missing_key_fails_explicitly(self):
        self.write_env(f"HTTP_PROXY='{self.proxy}'\nHTTPS_PROXY='{self.proxy}'\n")
        environment = {name: value for name, value in os.environ.items() if name not in web_env.ENV_NAMES}
        environment["UAEA_WEB_ENV_FILE"] = str(self.path)
        result = subprocess.run(
            ["bash", "scripts/start_h3_harness_interactive.sh", "--web-env-check"],
            cwd=web_env.PROJECT_ROOT, env=environment, capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("SERPAPI_KEY=MISSING", result.stderr)

    def test_h3_invalid_environment_stops_before_inference(self):
        with patch.object(interactive_repl, "load_web_environment", side_effect=web_env.WebEnvironmentError("unsafe")), \
                patch.object(interactive_repl, "start_vllm") as start, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(interactive_repl.run(Mock()), 2)
        start.assert_not_called()

    def test_app_server_does_not_inherit_web_key(self):
        root = Path(self.tmp.name)
        app = interactive_repl.InteractiveAppServer(
            codex=root / "codex", codex_home=root / "home", workspace=root / "workspace",
            base_url="http://127.0.0.1:8002", adapter=Mock(),
            events_path=root / "events.jsonl", stderr_path=root / "stderr.log", turn_timeout=420,
        )
        with patch.dict(os.environ, {"SERPAPI_KEY": self.secret}), \
                patch.object(interactive_repl.subprocess, "Popen") as spawn, \
                patch.object(interactive_repl, "ProviderHistoryBridge"), \
                patch.object(interactive_repl.threading, "Thread"), \
                patch.object(app, "_request", side_effect=[{"result": {}}, {"result": {"thread": {"id": "test"}}}]):
            app.start()
            self.assertNotIn("SERPAPI_KEY", spawn.call_args.kwargs["env"])
            self.assertEqual(os.environ["SERPAPI_KEY"], self.secret)
        app.close()

    def test_vllm_does_not_inherit_web_key_or_change_profile(self):
        root = Path(self.tmp.name)
        (root / "bin").mkdir()
        (root / "bin" / "vllm").touch()
        (root / "config.json").write_text("{}", encoding="utf-8")
        with patch.dict(os.environ, {"SERPAPI_KEY": self.secret}), \
                patch.object(context_probe.subprocess, "Popen") as spawn:
            process = context_probe.start_vllm(32768, "http://127.0.0.1:8002", root / "vllm.log", root, root, 0.75)
            self.assertNotIn("SERPAPI_KEY", spawn.call_args.kwargs["env"])
            args = spawn.call_args.args[0]
            self.assertEqual(args[args.index("--max-model-len") + 1], "32768")
            self.assertEqual(args[args.index("--gpu-memory-utilization") + 1], "0.75")
            self.assertEqual(args[args.index("--port") + 1], "8002")
            self.assertEqual(args[args.index("--tool-call-parser") + 1], "hermes")
            self.assertIn("--enable-auto-tool-choice", args)
            process._uaea_log_file.close()

    def test_generation_diagnostic_launcher_keeps_identical_inference_options(self):
        root = Path(self.tmp.name)
        (root / "bin").mkdir()
        (root / "bin" / "vllm").touch()
        (root / "config.json").write_text("{}", encoding="utf-8")
        with patch.dict(os.environ, {"SERPAPI_KEY": self.secret}), \
                patch.object(context_probe.subprocess, "Popen") as spawn:
            baseline = context_probe.start_vllm(32768, "http://127.0.0.1:8002", root / "baseline.log", root, root, 0.75)
            baseline_command = spawn.call_args.args[0]
            baseline._uaea_log_file.close()
            diagnostic = context_probe.start_vllm(32768, "http://127.0.0.1:8002", root / "diagnostic.log", root, root, 0.75,
                                                 generation_diagnostics_path=root / "generation.jsonl")
            command = spawn.call_args.args[0]
            self.assertEqual(command[command.index("serve"):], baseline_command[1:])
            self.assertIn("h3_vllm_diagnostic_launcher.py", command[1])
            self.assertEqual(command[command.index("--diagnostic-path") + 1], str(root / "generation.jsonl"))
            self.assertNotIn("SERPAPI_KEY", spawn.call_args.kwargs["env"])
            diagnostic._uaea_log_file.close()


if __name__ == "__main__":
    unittest.main()
