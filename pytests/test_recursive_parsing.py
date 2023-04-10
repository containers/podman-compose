import argparse
import pytest
import subprocess
import os
from podman_compose import PodmanCompose, ComposeFileParsingCircularDependencyException
from pathlib import Path


NONEMPTY_STRING = "non_empty_string.yml"
TESTS_PATH = Path(__file__).parent / '../tests/'

def fake_podman_env():
    env_with_fake_podman = os.environ.copy()
    here = TESTS_PATH / 'fake_podman'
    env_with_fake_podman.update({
        'PATH': f"{here}:{os.getenv('PATH','')}"
    })
    return env_with_fake_podman

def MockedPodmanCompose(compose_file: Path, *args, **kwargs):
    pc = PodmanCompose()
    pc.global_args = argparse.Namespace(file=[str(compose_file)],
                                        project_name=None,
                                        env_file=NONEMPTY_STRING,
                                        no_pod=True, *args, **kwargs)
    return pc

def test_given_compose_file_and_no_deps_arg_when_run_then_only_one_service_is_up():
    # https://github.com/containers/podman-compose/issues/398

    run = subprocess.run([str((Path(__file__).parent / "../podman_compose.py").absolute()),
                          '--dry-run', '-f', str(TESTS_PATH /
                                                 'extends_to_be_run/docker-compose.yml'), 'run',
                         'sh', 'sh'],
                         env=fake_podman_env(),
                         stderr=subprocess.PIPE,
                         universal_newlines=True
                         )
    assert 'podman run' in run.stderr

def test_given_compose_file_with_mounts_when_parsing_then_mounts_resolved_correctly():
    # https://github.com/containers/podman-compose/issues/462
    pc = MockedPodmanCompose(
        TESTS_PATH / 'extends_valid_mounts_resolved/docker-compose.yml')
    pc._parse_compose_file()
    assert set([
        '/tmp/service_other-bash:/tmp/service_other-bash:rw',
        '/tmp/service_bash:/tmp/service_bash:rw']) == set(pc.services['other-bash']['volumes'])


def test_given_cli_volume_and_compose_file_volume_when_parsing_then_both_are_used():
    # https://github.com/containers/podman-compose/issues/464
    run = subprocess.run([str((Path(__file__).parent / "../podman_compose.py").absolute()),
                          '--dry-run', '-f', str(TESTS_PATH /
                                                 'file_and_cli_mounts/docker-compose.yml'), 'run',
                          '-v', '/tmp/test:/tmp/test', 'sh', 'sh'],
                         env=fake_podman_env(),
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         universal_newlines=True
                         )
    assert '-v /tmp/test:/tmp/test' in run.stderr
    assert '-v /tmp/service_sh:/tmp/service_sh' in run.stderr

def test_given_ping_pong_dependencies_between_two_files_when_parsing_then_resolved_correctly():
    # https://github.com/containers/podman-compose/issues/465
    pc = MockedPodmanCompose(
        TESTS_PATH / 'extends_recursive/docker-compose.yml')
    pc._parse_compose_file()
    assert pc.services['sh1'].items() >= {
        'image': 'busybox',
        'volumes': ['/host/7:/cnt/7:rw', '/host/4:/cnt/4:rw', '/host/1:/cnt/1:rw']}.items()
    assert pc.services['sh2'].items() >= {
        'image': 'busybox',
        'volumes': ['/host/7:/cnt/7:rw']}.items()
    assert pc.services['sh3'].items() >= {
        'image': 'busybox',
        'volumes': ['/host/7:/cnt/7:rw']}.items()


def tests_given_compose_file_with_circular_dependency_when_parsing_then_raises_exception():
    # https://github.com/containers/podman-compose/issues/465
    pc = MockedPodmanCompose(
        TESTS_PATH / 'extends_recursive_circular/docker-compose.yml')
    with pytest.raises(ComposeFileParsingCircularDependencyException) as e:
        pc._parse_compose_file()
