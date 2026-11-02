# SPDX-License-Identifier: GPL-2.0

import io
import unittest

from podman_compose import load_yaml_or_die


class TestLoadYamlOrDie(unittest.TestCase):
    def test_parser_error_reports_clean_error(self) -> None:
        stream = io.StringIO("services:\n  web:\n    ports: [::]:8000:8000\n")

        with self.assertLogs("podman_compose", level="CRITICAL") as logs:
            with self.assertRaises(SystemExit) as ex:
                load_yaml_or_die("docker-compose.yml", stream)

        self.assertEqual(ex.exception.code, 1)
        self.assertEqual(
            logs.output[0],
            "CRITICAL:podman_compose:Compose file contains an error:\n"
            "while parsing a flow node\n"
            "expected the node content, but found ':'\n"
            '  in "<file>", line 3, column 13',
        )
