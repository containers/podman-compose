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
        decoded_out = out.decode('utf-8')
        decoded_err = err.decode('utf-8')
        self.assertEqual(
            returncode,
            expected_returncode,
            f"Invalid return code of process {returncode} != {expected_returncode}\n"
            f"stdout: {decoded_out}\nstderr: {decoded_err}\n",
        )
        return out, err
