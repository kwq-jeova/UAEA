from __future__ import annotations

import argparse
import json
import os
import shlex
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import MutableMapping


ENV_NAMES = frozenset({
    "SERPAPI_KEY", "HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
    "NO_PROXY", "no_proxy",
})
PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOOPBACK_HOSTS = ("localhost", "127.0.0.1", "::1")


class WebEnvironmentError(ValueError):
    pass


def private_env_path() -> Path:
    return Path(os.environ.get("UAEA_WEB_ENV_FILE", "~/.config/uaea/web.env")).expanduser()


def _check_private_path(path: Path) -> None:
    if path.resolve().is_relative_to(PROJECT_ROOT):
        raise WebEnvironmentError("Private Web environment must be outside the repository.")


def _read_private_env(path: Path) -> dict[str, str]:
    _check_private_path(path)
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise WebEnvironmentError("Private Web environment must be a regular file.")
            if os.name == "posix":
                if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
                    raise WebEnvironmentError("Private Web environment must be owned by you with mode 600.")
            content = stream.read(16_385)
        if len(content) > 16_384:
            raise WebEnvironmentError("Private Web environment exceeds the size limit.")
        lines = content.decode("utf-8").splitlines()
    except (OSError, UnicodeError):
        raise WebEnvironmentError("Cannot safely read the private Web environment.") from None

    values: dict[str, str] = {}
    for number, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        name, separator, value = line.partition("=")
        name = name.strip()
        if not separator or name not in ENV_NAMES or name in values:
            raise WebEnvironmentError(f"Invalid private environment assignment at line {number}.")
        try:
            parts = shlex.split(value, comments=True, posix=True)
        except ValueError:
            raise WebEnvironmentError(f"Invalid private environment value at line {number}.") from None
        if len(parts) > 1:
            raise WebEnvironmentError(f"Invalid private environment value at line {number}.")
        values[name] = parts[0] if parts else ""
    return values


def _proxy_pair(values: MutableMapping[str, str], upper: str) -> str:
    candidates = {values[name].strip() for name in (upper, upper.lower()) if values.get(name, "").strip()}
    if len(candidates) > 1:
        raise WebEnvironmentError(f"Conflicting {upper} aliases; use the same value.")
    return next(iter(candidates), "")


def _validate_proxy(value: str) -> None:
    try:
        parsed = urllib.parse.urlsplit(value)
        valid = (
            parsed.scheme in {"http", "https"} and parsed.hostname
            and parsed.path in {"", "/"} and not parsed.query and not parsed.fragment
            and (parsed.port is None or 1 <= parsed.port <= 65535)
            and not any(char.isspace() for char in value)
        )
    except ValueError:
        valid = False
    if not valid:
        raise WebEnvironmentError("Invalid proxy configuration; an HTTP(S) proxy URL is required.")


def load_web_environment(
    *, path: Path | None = None, environ: MutableMapping[str, str] | None = None,
    require_key: bool = False, require_proxy: bool = False, report: bool = True,
) -> dict[str, str]:
    target = os.environ if environ is None else environ
    path = private_env_path() if path is None else path
    _check_private_path(path)
    file_values = _read_private_env(path) if path.exists() or path.is_symlink() else {}
    updates: dict[str, str] = {}
    for upper in ("HTTP_PROXY", "HTTPS_PROXY"):
        value = _proxy_pair(target, upper) or _proxy_pair(file_values, upper)
        if value:
            _validate_proxy(value)
            updates[upper] = updates[upper.lower()] = value
    bypass = list(LOOPBACK_HOSTS)
    for values in (file_values, target):
        for name in ("NO_PROXY", "no_proxy"):
            bypass.extend(part.strip() for part in values.get(name, "").split(",") if part.strip())
    updates["NO_PROXY"] = updates["no_proxy"] = ",".join(dict.fromkeys(bypass))
    key = target.get("SERPAPI_KEY", "").strip() or file_values.get("SERPAPI_KEY", "").strip()
    if key and any(char.isspace() for char in key):
        raise WebEnvironmentError("Invalid SERPAPI_KEY format.")
    if key:
        updates["SERPAPI_KEY"] = key
    key_present = bool(key)
    proxy_present = all(updates.get(name) for name in ("HTTP_PROXY", "HTTPS_PROXY"))
    if report:
        print(f"[WEB ENV] private_file={'SET' if file_values else 'MISSING'}", file=sys.stderr)
        for name in ("HTTP_PROXY", "HTTPS_PROXY", "SERPAPI_KEY"):
            print(f"[WEB ENV] {name}={'SET' if updates.get(name) else 'MISSING'}", file=sys.stderr)
        if not proxy_present:
            print("[WEB ENV] WARNING: proxy configuration is incomplete.", file=sys.stderr)
        if not key_present:
            print("[WEB ENV] WARNING: SERPAPI_KEY missing; authenticated SerpApi search is unavailable.", file=sys.stderr)
    if require_key and not key_present:
        raise WebEnvironmentError("SERPAPI_KEY is required; configure the private Web environment.")
    if require_proxy and not proxy_present:
        raise WebEnvironmentError("HTTP_PROXY and HTTPS_PROXY are required.")
    target.update(updates)
    return {name: ("SET" if target.get(name) else "MISSING") for name in ENV_NAMES}


def initialize_private_env(path: Path | None = None) -> Path:
    path = private_env_path() if path is None else path
    _check_private_path(path)
    values = {"SERPAPI_KEY": ""}
    for upper in ("HTTP_PROXY", "HTTPS_PROXY"):
        value = _proxy_pair(os.environ, upper)
        if value:
            _validate_proxy(value)
        values[upper] = values[upper.lower()] = value
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise WebEnvironmentError("Private Web environment already exists; it was not overwritten.") from None
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
        if os.name == "posix":
            os.fchmod(stream.fileno(), 0o600)
        stream.write("# Private UAEA Web environment. Never commit or print this file.\n")
        for name, value in values.items():
            stream.write(f"{name}={shlex.quote(value)}\n")
        stream.flush()
        os.fsync(stream.fileno())
    return path


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def serpapi_environment_smoke() -> dict[str, object]:
    # The API requires a query credential; keep this URL only in memory, never in provenance.
    query = urllib.parse.urlencode({
        "engine": "google", "q": "AI agent research", "num": 3,
        "api_key": os.environ["SERPAPI_KEY"],
    })
    request = urllib.request.Request(
        "https://serpapi.com/search.json?" + query,
        headers={"User-Agent": "UAEA-WebEnvironment-Smoke/1.0"},
    )
    try:
        opener = urllib.request.build_opener(_NoRedirect())
        with opener.open(request, timeout=30) as response:
            body = response.read(2_000_001)
            if len(body) > 2_000_000:
                raise WebEnvironmentError("SerpApi response exceeds the smoke-test limit.")
            payload = json.loads(body)
    except urllib.error.HTTPError as exc:
        raise WebEnvironmentError(f"SerpApi smoke failed: HTTP {exc.code}; response and request URL withheld.") from None
    except (urllib.error.URLError, OSError, UnicodeError, ValueError):
        raise WebEnvironmentError("SerpApi smoke failed: transport or response error; details withheld.") from None
    if not isinstance(payload, dict):
        raise WebEnvironmentError("SerpApi smoke failed: invalid response structure.")
    metadata = payload.get("search_metadata", {})
    parameters = payload.get("search_parameters", {})
    results = payload.get("organic_results", [])
    if (not isinstance(metadata, dict) or not isinstance(parameters, dict)
            or not isinstance(results, list) or payload.get("error")
            or metadata.get("status") != "Success" or parameters.get("engine") != "google"
            or not any(isinstance(item, dict) and item.get("link") for item in results)):
        raise WebEnvironmentError("SerpApi smoke failed: no confirmed Google organic results; details withheld.")
    return {"status": "PASS", "acquisition_service": "serpapi", "reported_engine": "google",
            "organic_result_count": len(results)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Private UAEA Web environment validation; never prints credentials.")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--init-private-env", action="store_true")
    actions.add_argument("--check", action="store_true")
    actions.add_argument("--serpapi-smoke", action="store_true")
    args = parser.parse_args()
    try:
        if args.init_private_env:
            print(f"[WEB ENV] private template created: {initialize_private_env()}")
            return 0
        load_web_environment(require_key=True, require_proxy=True)
        if args.serpapi_smoke:
            print(json.dumps(serpapi_environment_smoke(), sort_keys=True))
        return 0
    except WebEnvironmentError as exc:
        print(f"[WEB ENV] ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
