import os
import podman_compose

def test_case_for(folder):
    os.chdir(folder)
    podman_compose.podman_compose.run(["build"])
