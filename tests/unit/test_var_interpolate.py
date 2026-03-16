# SPDX-License-Identifier: GPL-2.0

import subprocess
import unittest
from typing import Union

from parameterized import parameterized

from podman_compose import var_interpolate


class TestVarInterpolate(unittest.TestCase):
    test_cases = [
        # 0. Substitution without braces
        ("Hello $NAME!", {"NAME": "Alice"}, "Hello Alice!", True),
        # 1. Substitution with braces
        ("Hello ${NAME}", {"NAME": "Alice"}, "Hello Alice", True),
        # 2. Unset variable (empty substitution)
        ("Hello ${NAME}", {}, "Hello ", True),
        # 3. Default if unset (:-)
        ("User: ${USER:-guest}", {}, "User: guest", True),
        # 4. Default if unset or empty (:-)
        ("User: ${USER:-guest}", {"USER": ""}, "User: guest", True),
        # 5. Default if unset (-)
        ("User: ${USER-guest}", {}, "User: guest", True),
        # 6. Default if unset but not if empty (-)
        ("User: ${USER-guest}", {"USER": ""}, "User: ", True),
        # 7. Required variable (error if unset or empty)
        ("Path: ${TEST_PATH:?TEST_PATH required}", {"TEST_PATH": "/bin"}, "Path: /bin", True),
        # 8. Required variable fails when missing
        (
            "Path: ${TEST_PATH:?TEST_PATH required}",
            {},
            ValueError("required variable TEST_PATH is missing a value: TEST_PATH required"),
            True,
        ),
        # 9. Required variable fails when empty (since :?)
        (
            "Path: ${TEST_PATH:?TEST_PATH required}",
            {"TEST_PATH": ""},
            ValueError("required variable TEST_PATH is missing a value: TEST_PATH required"),
            True,
        ),
        # 10. Required variable (no colon, fails only if unset)
        ("Config: ${CFG?missing}", {"CFG": "cfg.yaml"}, "Config: cfg.yaml", True),
        # 11. Required variable fails when unset
        (
            "Config: ${CFG?missing}",
            {},
            ValueError("required variable CFG is missing a value: missing"),
            True,
        ),
        # 12. Required variable passes even if empty (no colon)
        ("Config: ${CFG?missing}", {"CFG": ""}, "Config: ", True),
        # 13. Alternative if set (:+)
        ("Alt: ${MODE:+active}", {"MODE": "1"}, "Alt: active", True),
        # 14. Alternative if set, variable empty (still uses alt)
        ("Alt: ${MODE+active}", {"MODE": ""}, "Alt: active", True),
        # 15. Alternative if not set (+)
        ("Alt: ${MODE+active}", {}, "Alt: ", True),
        # 16. Combination of multiple vars
        ("${GREETING:-Hi}, ${NAME:-stranger}!", {}, "Hi, stranger!", True),
        # 17. Mix of required and default
        ("${ENV:?Missing ENV} - ${SERVICE:-api}", {"ENV": "prod"}, "prod - api", True),
        # 18. Default values with spaces
        ("${USER:-default user}", {}, "default user", True),
        # 19. Escaped dollar sign
        (
            "Price: $$${AMOUNT}",
            {"AMOUNT": "100"},
            "Price: $100",
            False,  # In POSIX shells, $$ becomes PID, so skip shell test
        ),
        # 20. Empty variable substitution
        ("Value: ${VAR}", {"VAR": ""}, "Value: ", True),
        # 21. Nested default (inner default resolves)
        ("${OUTER:-${INNER:-default}}", {}, "default", True),
        # 22. Nested default (inner variable exists)
        ("${OUTER:-${INNER:-default}}", {"INNER": "inner_value"}, "inner_value", True),
        # 23. Nested default (outer variable exists)
        (
            "${OUTER:-${INNER:-default}}",
            {"OUTER": "outer_value", "INNER": "inner_value"},
            "outer_value",
            True,
        ),
        # 24. Nested fallback chain
        ("${A:-${B:-${C:-final}}}", {}, "final", True),
        # 25. Nested fallback uses middle value
        ("${A:-${B:-${C:-final}}}", {"B": "mid"}, "mid", True),
        # 26. Nested fallback uses top value
        ("${A:-${B:-${C:-final}}}", {"A": "top"}, "top", True),
        # 27. Nested required variable message
        ("${MAIN:-${BACKUP:?Missing BACKUP}}", {"BACKUP": "backup_value"}, "backup_value", True),
        # 28. Nested required variable fails (inner missing)
        (
            "${MAIN:-${BACKUP:?Missing BACKUP}}",
            {},
            ValueError("required variable BACKUP is missing a value: Missing BACKUP"),
            True,
        ),
        # 29. Nested default with error in inner fallback
        ("${X:-${Y:?Y required}}", {"Y": "ok"}, "ok", True),
        # 30. Nested default that triggers inner error
        (
            "${X:-${Y:?Y required}}",
            {},
            ValueError("required variable Y is missing a value: Y required"),
            True,
        ),
        # 31. Inner nested default that is never triggered because outer value is used
        ("${X:-${Y:?Y required}}", {"X": "ok"}, "ok", True),
        # 32. Nested alternative expansion
        (
            "${VAR:+${ALT:-default_alt}}",
            {"VAR": "something", "ALT": "alt_value"},
            "alt_value",
            True,
        ),
        # 33. Nested alternative fallback
        ("${VAR:+${ALT:-default_alt}}", {"VAR": "something"}, "default_alt", True),
        # 34. Nested with unset outer, inner provides default
        ("${OUTER:-prefix_${INNER:-none}}", {}, "prefix_none", True),
        # 35. Nested with inner variable set
        ("${OUTER:-prefix_${INNER:-none}}", {"INNER": "abc"}, "prefix_abc", True),
        # 36. Outer required, inner fallback
        ("${REQ:?Missing ${ALT:-something}}", {"REQ": "value"}, "value", True),
        # 37. Outer required triggers nested message
        (
            "${REQ:?Missing ${ALT:-something}}",
            {},
            ValueError("required variable REQ is missing a value: Missing something"),
            True,
        ),
        # 38. Nested alternative chain
        ("${A:+${B:+${C:-end}}}", {"A": "1", "B": "1", "C": "final"}, "final", True),
        # 39. Nested alternative where middle missing
        ("${A:+${B:+${C:-end}}}", {"A": "1"}, "", True),
        # 40. Triple nested default with middle empty
        ("${A:-${B:-${C:-${D:-default}}}}", {"B": ""}, "default", True),
        # 41. Mixed chain: required + default + alternative
        ("${ENV:-${FALLBACK:+${ALT:-alt_value}}}", {"FALLBACK": "1"}, "alt_value", True),
    ]

    @parameterized.expand(test_cases)
    def test_var_interpolate(
        self,
        to_interpolate: str,
        var_values: dict[str, str],
        expected: Union[str, ValueError],
        compare_shell_evaluation: bool,
    ) -> None:
        try:
            result = var_interpolate(to_interpolate, var_values)
            self.assertEqual(result, expected)
        except ValueError as e:
            self.assertTrue(
                isinstance(expected, ValueError),
                msg=f"Expected ValueError for input: {to_interpolate}",
            )
            self.assertEqual(str(e), str(expected))

        if not compare_shell_evaluation:
            return

        # Ensure that the behavior matches the behavior of POSIX shells
        process = subprocess.Popen(
            f'echo "{to_interpolate}"',
            env=var_values,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, _ = process.communicate()
        shell_result = stdout.rstrip(b'\n').decode()
        exit_code = process.returncode
        if isinstance(expected, ValueError):
            error_msg = f"Expected non-zero return code success for input: {to_interpolate}"
            self.assertNotEqual(exit_code, 0, msg=error_msg)
        else:
            self.assertEqual(shell_result, expected)
