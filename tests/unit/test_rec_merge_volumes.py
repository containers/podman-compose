# SPDX-License-Identifier: GPL-2.0
from __future__ import annotations

import unittest
from typing import Any

from parameterized import parameterized

from podman_compose import rec_merge


def bind(source: str, target: str, **options: Any) -> dict[str, Any]:
    return {"type": "bind", "source": source, "target": target, **options}


class TestRecMergeVolumes(unittest.TestCase):
    """Test that rec_merge replaces service volumes with the same mount target."""

    @parameterized.expand([
        (
            "short_syntax",
            ["./a:/data", "./b:/other:ro"],
            ["./c:/data:z"],
            ["./b:/other:ro", "./c:/data:z"],
        ),
        (
            "long_syntax",
            [bind("./a", "/data", read_only=True), bind("./b", "/other")],
            [bind("./c", "/data")],
            [bind("./b", "/other"), bind("./c", "/data")],
        ),
        (
            "long_syntax_overrides_short_syntax",
            ["./a:/data", "./b:/other"],
            [bind("./c", "/data")],
            ["./b:/other", bind("./c", "/data")],
        ),
        (
            "short_syntax_overrides_long_syntax",
            [bind("./a", "/data"), bind("./b", "/other")],
            ["./c:/data"],
            [bind("./b", "/other"), "./c:/data"],
        ),
        (
            "different_targets_are_kept",
            [bind("./a", "/data"), "named:/cache"],
            [bind("./c", "/logs"), "/anonymous"],
            [bind("./a", "/data"), "named:/cache", bind("./c", "/logs"), "/anonymous"],
        ),
    ])
    def test_rec_merge_volumes(
        self,
        desc: str,
        base: list[Any],
        override: list[Any],
        expected: list[Any],
    ) -> None:
        result = rec_merge({"volumes": base}, {"volumes": override})
        self.assertEqual(result["volumes"], expected)
