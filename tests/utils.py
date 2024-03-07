import subprocess


def capture(command):
    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = proc.communicate()

    print("stdout:\n" + out.decode('utf-8'))
    print("stderr:\n" + err.decode('utf-8'))

    return out, err, proc.returncode
