from __future__ import annotations

import codecs
import os
import sys
import time
from typing import Callable


def read_user_input(prompt: str, *, on_idle: Callable[[], None] | None = None,
                    timeout: float | None = None) -> str:
    """Read one REPL line using the terminal's native editor by default."""

    mode = os.environ.get("UAEA_REPL_INPUT_MODE", "basic").strip().lower()
    if mode in {"raw", "utf8-raw"}:
        if os.name == "posix" and sys.stdin.isatty() and sys.stdout.isatty():
            return _read_raw_utf8_line(prompt, on_idle=on_idle, timeout=timeout)
        if on_idle is not None or timeout is not None:
            return _read_polled_line(prompt, on_idle, timeout)
        return input(prompt)
    if on_idle is not None or timeout is not None:
        return _read_polled_line(prompt, on_idle, timeout)
    _enable_readline_if_available()
    return input(prompt)


def _enable_readline_if_available() -> None:
    if os.name != "posix":
        return
    try:
        import readline  # noqa: F401
    except ImportError:
        return


def _wait_readable(fd, deadline, on_idle):
    import select
    while True:
        if on_idle:
            on_idle()
        remaining = None if deadline is None else deadline - time.monotonic()
        if remaining is not None and remaining <= 0:
            raise TimeoutError("User input timed out")
        if select.select([fd], [], [], min(0.2, remaining) if remaining is not None else 0.2)[0]:
            return


def _read_polled_line(prompt, on_idle, timeout):
    sys.stdout.write(prompt)
    sys.stdout.flush()
    deadline = None if timeout is None else time.monotonic() + timeout
    _wait_readable(sys.stdin.fileno(), deadline, on_idle)
    value = sys.stdin.readline()
    if not value:
        raise EOFError
    return value.rstrip("\r\n")


def _read_raw_utf8_line(prompt: str, *, on_idle=None, timeout=None) -> str:
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    state = _Utf8LineState()
    deadline = None if timeout is None else time.monotonic() + timeout
    sys.stdout.write(prompt)
    sys.stdout.flush()
    try:
        tty.setraw(fd)
        while True:
            if on_idle is not None or timeout is not None:
                _wait_readable(fd, deadline, on_idle)
            data = os.read(fd, 1)
            action = state.feed(data)
            if action == "submit":
                sys.stdout.write("\n")
                sys.stdout.flush()
                return state.text()
            if action == "interrupt":
                raise KeyboardInterrupt
            if action == "eof":
                raise EOFError
            if action == "redraw":
                _redraw(prompt, state.text())
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _redraw(prompt: str, value: str) -> None:
    sys.stdout.write("\r\x1b[2K" + prompt + value)
    sys.stdout.flush()


class _Utf8LineState:
    def __init__(self) -> None:
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self._chars: list[str] = []
        self._escape_bytes_to_ignore = 0

    def text(self) -> str:
        return "".join(self._chars)

    def feed(self, data: bytes) -> str:
        if self._escape_bytes_to_ignore > 0:
            self._escape_bytes_to_ignore -= 1
            return "redraw"
        if data in {b"\r", b"\n"}:
            self._flush_decoder()
            return "submit"
        if data == b"\x03":
            return "interrupt"
        if data == b"\x04":
            return "eof" if not self._chars else "submit"
        if data == b"\x15":
            self._decoder.reset()
            self._chars.clear()
            return "redraw"
        if data in {b"\x7f", b"\b"}:
            self._decoder.reset()
            if self._chars:
                self._chars.pop()
            return "redraw"
        if data == b"\x1b":
            self._decoder.reset()
            self._escape_bytes_to_ignore = 2
            return "redraw"

        decoded = self._decoder.decode(data, final=False)
        for char in decoded:
            if char == "\t":
                self._chars.append(" ")
            elif char >= " " and not 0xD800 <= ord(char) <= 0xDFFF:
                self._chars.append(char)
        return "redraw" if decoded else "continue"

    def _flush_decoder(self) -> None:
        decoded = self._decoder.decode(b"", final=True)
        for char in decoded:
            if char >= " " and not 0xD800 <= ord(char) <= 0xDFFF:
                self._chars.append(char)
        self._decoder.reset()
