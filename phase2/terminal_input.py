from __future__ import annotations

import codecs
import os
import sys


def read_user_input(prompt: str) -> str:
    """Read one REPL line using the terminal's native editor by default."""

    mode = os.environ.get("UAEA_REPL_INPUT_MODE", "basic").strip().lower()
    if mode in {"raw", "utf8-raw"}:
        if os.name == "posix" and sys.stdin.isatty() and sys.stdout.isatty():
            return _read_raw_utf8_line(prompt)
        return input(prompt)
    _enable_readline_if_available()
    return input(prompt)


def _enable_readline_if_available() -> None:
    if os.name != "posix":
        return
    try:
        import readline  # noqa: F401
    except ImportError:
        return


def _read_raw_utf8_line(prompt: str) -> str:
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    state = _Utf8LineState()
    sys.stdout.write(prompt)
    sys.stdout.flush()
    try:
        tty.setraw(fd)
        while True:
            data = sys.stdin.buffer.read(1)
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
