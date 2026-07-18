# SPDX-License-Identifier: GPL-2.0
from __future__ import annotations

import unittest
from typing import Any

from podman_compose import flat_deps
from podman_compose import normalize
from podman_compose import resolve_extends


class TestResolveExtendsDependents(unittest.TestCase):
    """Regression test: resolve_extends used to crash with
    AttributeError: 'set' object has no attribute 'extend'
    whenever a service that is itself depended on by another service
    was also used as the target of an `extends:`.

    flat_deps(services, with_extends=True) populates a "_dependents" set on
    every service that has a dependent. resolve_extends() already stripped
    the internal "_deps" set from the extends source before merging it, but
    not "_dependents" - so when both the extends source and the extending
    service carried a "_dependents" set, rec_merge_one() tried to
    list.extend() a set and blew up.
    """

    def test_extends_target_with_dependents_does_not_crash(self) -> None:
        compose: dict[str, Any] = {
            "services": {
                "base": {"image": "busybox"},
                "app": {
                    "extends": {"service": "base"},
                    "depends_on": ["base"],
                },
                "app2": {
                    "image": "busybox",
                    "depends_on": ["app"],
                },
            }
        }
        services = normalize(compose)["services"]
        flat_deps(services, with_extends=True)

        # should not raise AttributeError: 'set' object has no attribute 'extend'
        resolve_extends(services, list(services.keys()), {})

        self.assertEqual(services["app"]["image"], "busybox")
