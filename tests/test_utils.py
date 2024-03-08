# SPDX-License-Identifier: GPL-2.0

import subprocess


class RunSubprocessMixin:
    def run_subprocess(self, args):
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = proc.communicate()
        return out, err, proc.returncode

    def run_subprocess_assert_returncode(self, args, expected_returncode=0):
        out, err, returncode = self.run_subprocess(args)
        self.assertEqual(
            returncode,
            expected_returncode,
            f"Invalid return code of process {returncode} != {expected_returncode}\n"
            f"stdout: {out}\nstderr: {err}\n",
        )
        return out, err
