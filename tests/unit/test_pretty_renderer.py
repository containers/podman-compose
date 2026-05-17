# SPDX-License-Identifier: GPL-2.0

import argparse
import io
import unittest

from podman_compose import PlainRenderer
from podman_compose import PrettyRenderer
from podman_compose import UpStatusLine
from podman_compose import create_up_renderer
from podman_compose import should_use_color_output
from podman_compose import should_use_pretty_output


class FakeTTY(io.StringIO):
    def __init__(self, is_tty: bool, encoding: str = "utf-8") -> None:
        super().__init__()
        self._is_tty = is_tty
        self._encoding = encoding

    def isatty(self) -> bool:
        return self._is_tty

    @property
    def encoding(self) -> str:
        return self._encoding


class TestPrettyRenderer(unittest.TestCase):
    def test_should_use_pretty_output_requires_tty(self) -> None:
        args = argparse.Namespace(no_color=False)
        sink = FakeTTY(False)
        self.assertFalse(should_use_pretty_output(args, {}, sink))

    def test_should_use_pretty_output_tty_enabled(self) -> None:
        args = argparse.Namespace(no_color=False)
        sink = FakeTTY(True)
        self.assertTrue(should_use_pretty_output(args, {}, sink))

    def test_should_use_color_output_disabled_by_no_color(self) -> None:
        args = argparse.Namespace(no_color=False)
        sink = FakeTTY(True)
        self.assertFalse(should_use_color_output(args, {"NO_COLOR": "1"}, sink))

    def test_create_up_renderer_without_tty_uses_plain_renderer(self) -> None:
        args = argparse.Namespace(no_color=False)
        sink = FakeTTY(False)
        renderer = create_up_renderer(args, {}, sink, total=2, name_width=10)
        self.assertIsInstance(renderer, PlainRenderer)

    def test_ascii_fallback_symbols(self) -> None:
        sink = FakeTTY(True, encoding="ascii")
        renderer = PrettyRenderer(
            sink,
            total=1,
            use_color=False,
            use_unicode=False,
            name_width=8,
        )
        renderer.begin()
        renderer.emit(UpStatusLine("Container", "demo", "Healthy", "success", final=True))
        renderer.finish()

        output = sink.getvalue()
        self.assertIn(" + Container", output)
        self.assertNotIn("✔", output)

    def test_alignment_with_long_names(self) -> None:
        sink = FakeTTY(True)
        renderer = PrettyRenderer(
            sink,
            total=2,
            use_color=False,
            use_unicode=True,
            name_width=22,
        )
        renderer.emit(UpStatusLine("Container", "short", "Healthy", "success", final=True))
        renderer.emit(
            UpStatusLine(
                "Container",
                "very-very-long-container",
                "Recreated",
                "success",
                final=True,
            )
        )

        lines = sink.getvalue().splitlines()
        self.assertEqual(lines[0], " ✔ Container short                  Healthy")
        self.assertEqual(lines[1], " ✔ Container very-very-long-container Recreated")

    def test_snapshot_pretty_output_with_color(self) -> None:
        args = argparse.Namespace(no_color=False)
        sink = FakeTTY(True)
        renderer = create_up_renderer(args, {}, sink, total=1, name_width=12)
        self.assertIsInstance(renderer, PrettyRenderer)

        renderer.begin()
        renderer.emit(UpStatusLine("Container", "xtm-redis-1", "Healthy", "success", final=True))
        renderer.finish()

        expected = (
            "\n"
            "\x1b[1m[+] up 0/1\x1b[0m\n"
            " \x1b[1;32m✔\x1b[0m Container xtm-redis-1  Healthy\n"
            "\x1b[1m[+] up 1/1\x1b[0m\n"
        )
        self.assertEqual(sink.getvalue(), expected)
