from __future__ import annotations

import unittest

from phase2.terminal_input import _Utf8LineState


class TerminalInputTests(unittest.TestCase):
    def test_backspace_removes_one_complete_chinese_character(self):
        state = _Utf8LineState()

        for byte in "中文".encode("utf-8"):
            state.feed(bytes([byte]))
        state.feed(b"\x7f")
        action = state.feed(b"\n")

        self.assertEqual(action, "submit")
        self.assertEqual(state.text(), "中")

    def test_backspace_after_chinese_character_allows_clean_ascii_continuation(self):
        state = _Utf8LineState()

        for byte in "查".encode("utf-8"):
            state.feed(bytes([byte]))
        state.feed(b"\x7f")
        state.feed(b"a")
        state.feed(b"\n")

        self.assertEqual(state.text(), "a")

    def test_ctrl_u_clears_current_line(self):
        state = _Utf8LineState()

        for byte in "查询LoRA".encode("utf-8"):
            state.feed(bytes([byte]))
        state.feed(b"\x15")
        for byte in "LoRA".encode("utf-8"):
            state.feed(bytes([byte]))
        state.feed(b"\n")

        self.assertEqual(state.text(), "LoRA")

    def test_arrow_escape_sequence_is_not_inserted_into_input(self):
        state = _Utf8LineState()

        state.feed(b"a")
        state.feed(b"\x1b")
        state.feed(b"[")
        state.feed(b"D")
        state.feed(b"b")
        state.feed(b"\n")

        self.assertEqual(state.text(), "ab")


if __name__ == "__main__":
    unittest.main()
