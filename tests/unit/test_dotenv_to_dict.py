# SPDX-License-Identifier: GPL-2.0

import os
import tempfile
import unittest
from unittest import mock

from parameterized import parameterized

from podman_compose import PodmanComposeError
from podman_compose import dotenv_to_dict


class TestDotenvToDict(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def write_env(self, content: str) -> str:
        path = os.path.join(self._tmp.name, ".env")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path

    def test_interpolates_from_os_environ(self) -> None:
        path = self.write_env("FOO=${BAR}\n")
        with mock.patch.dict(os.environ, {"BAR": "bar"}, clear=True):
            self.assertEqual(dotenv_to_dict(path), {"FOO": "bar"})

    def test_interpolates_from_earlier_entry(self) -> None:
        path = self.write_env("BAR=bar\nFOO=${BAR}\n")
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(dotenv_to_dict(path), {"BAR": "bar", "FOO": "bar"})

    def test_missing_variable_resolves_to_empty_string(self) -> None:
        path = self.write_env("FOO=${MISSING}\n")
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(dotenv_to_dict(path), {"FOO": ""})

    def test_explicit_environ_overrides_os_environ(self) -> None:
        path = self.write_env("FOO=${BAR}\n")
        with mock.patch.dict(os.environ, {"BAR": "from-os"}, clear=True):
            self.assertEqual(dotenv_to_dict(path, {"BAR": "from-arg"}), {"FOO": "from-arg"})

    def test_missing_file_returns_empty_dict(self) -> None:
        self.assertEqual(dotenv_to_dict(os.path.join(self._tmp.name, "does-not-exist")), {})

    def test_unreadable_file_raises(self) -> None:
        path = self.write_env("FOO=bar\n")
        with mock.patch("builtins.open", side_effect=PermissionError("denied")):
            with self.assertRaises(PodmanComposeError) as ctx:
                dotenv_to_dict(path, {})
        self.assertEqual(str(ctx.exception), f"Could not read env file {path}: denied")

    def test_environ_takes_precedence_over_file_value_for_interpolation(self) -> None:
        path = self.write_env("BAR=from-file\nFOO=${BAR}\n")
        self.assertEqual(
            dotenv_to_dict(path, {"BAR": "from-environ"}),
            {"BAR": "from-file", "FOO": "from-environ"},
        )

    @parameterized.expand([
        ("braced", "FOO=${BAR}\n", "bar"),
        ("bare", "FOO=$BAR\n", "bar"),
        ("default_nonempty", "FOO=${MISSING:-def}\n", "def"),
        ("default_set", "FOO=${MISSING-def}\n", "def"),
        ("alternative_nonempty", "FOO=${BAR:+alt}\n", "alt"),
        ("alternative_set", "FOO=${BAR+alt}\n", "alt"),
        ("nested_default", "FOO=${MISSING:-$BAR}\n", "bar"),
        ("nested_braced_default", "FOO=${MISSING:-${BAR}}\n", "bar"),
        ("embedded", "FOO=pre${BAR}post\n", "prebarpost"),
        ("escaped_dollar", "FOO=$$BAR\n", "$BAR"),
        ("literal_dollar", "FOO=$\n", "$"),
    ])
    def test_interpolation_syntax(self, _name: str, content: str, expected: str) -> None:
        path = self.write_env(content)
        self.assertEqual(dotenv_to_dict(path, {"BAR": "bar"}), {"FOO": expected})

    def test_single_quoted_value_is_literal(self) -> None:
        path = self.write_env("FOO='$BAR'\n")
        self.assertEqual(dotenv_to_dict(path, {"BAR": "bar"}), {"FOO": "$BAR"})

    def test_double_quoted_value_is_interpolated(self) -> None:
        path = self.write_env('FOO="$BAR"\n')
        self.assertEqual(dotenv_to_dict(path, {"BAR": "bar"}), {"FOO": "bar"})

    def test_required_variable_missing_raises(self) -> None:
        path = self.write_env("FOO=${MISSING:?err}\n")
        with self.assertRaises(PodmanComposeError) as ctx:
            dotenv_to_dict(path, {})
        self.assertEqual(
            str(ctx.exception),
            f"{path}:1: required variable MISSING is missing a value: err",
        )

    def test_invalid_interpolation_reports_file_and_line(self) -> None:
        path = self.write_env("BAR=bar\nFOO=${}\n")
        with self.assertRaises(PodmanComposeError) as ctx:
            dotenv_to_dict(path, {})
        self.assertEqual(
            str(ctx.exception),
            f"{path}:2: Invalid interpolation format: ${{}}."
            " You may need to escape any $ with another $",
        )

    def test_malformed_line_warns_and_is_skipped(self) -> None:
        path = self.write_env("GOOD=1\nBAD LINE HERE\nOTHER=2\n")
        with self.assertLogs("podman_compose", level="WARNING") as ctx:
            self.assertEqual(dotenv_to_dict(path, {}), {"GOOD": "1", "OTHER": "2"})
        self.assertEqual(
            ctx.output[0],
            f"WARNING:podman_compose:{path}: could not parse statement starting at line 2",
        )

    def test_raw_format_keeps_values_verbatim(self) -> None:
        path = self.write_env('A=$BAR\nB="quoted"\nC=\'single\'\nD=plain # comment\nE=has=equals\n')
        self.assertEqual(
            dotenv_to_dict(path, {"BAR": "bar"}, raw=True),
            {
                "A": "$BAR",
                "B": '"quoted"',
                "C": "'single'",
                "D": "plain # comment",
                "E": "has=equals",
            },
        )

    def test_raw_format_preserves_whitespace_and_skips_invalid_lines(self) -> None:
        path = self.write_env("A=trail   \nB=  lead\nC=\nBARE\n# comment\nD=bare\n")
        self.assertEqual(
            dotenv_to_dict(path, {}, raw=True),
            {"A": "trail   ", "B": "  lead", "C": "", "D": "bare"},
        )
