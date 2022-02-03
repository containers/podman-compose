import argparse
import json
import os
import random
import subprocess
import time

from threading import Thread

from .classes import cmd_parse, cmd_run, PodmanCompose
from .helpers import (
    norm_as_list,
    log,
    container_to_args,
    parse_short_mount,
    is_str,
    fix_mount_dict,
    container_to_ulimit_args
)

###################
# actual commands
###################
__version__ = '1.0.3'
podman_compose = PodmanCompose()

@cmd_run(podman_compose, 'version', 'show version')
def compose_version(compose, args):
    if getattr(args, 'short', False): 
        print(__version__)
        return
    if getattr(args, 'format', 'pretty') == 'json':
        res = {"version": __version__}
        print(json.dumps(res))
        return
    log("podman-composer version", __version__)
    compose.podman.run(["--version"], "", [], sleep=0)

def is_local(container: dict) -> bool:
    """Test if a container is local, i.e. if it is
    * prefixed with localhost/
    * has a build section and is not prefixed
    """
    return (
        not "/" in container["image"]
        if "build" in container
        else container["image"].startswith("localhost/")
    )

@cmd_run(podman_compose, "pull", "pull stack images")
def compose_pull(compose, args):
    img_containers = [cnt for cnt in compose.containers if "image" in cnt]
    images = {cnt["image"] for cnt in img_containers}
    if not args.force_local:
        local_images = {cnt["image"] for cnt in img_containers if is_local(cnt)}
        images -= local_images
    for image in images:
        compose.podman.run([], "pull", [image], sleep=0)

@cmd_run(podman_compose, 'push', 'push stack images')
def compose_push(compose, args):
    services = set(args.services)
    for cnt in compose.containers:
        if 'build' not in cnt: continue
        if services and cnt['_service'] not in services: continue
        compose.podman.run([], "push", [cnt["image"]], sleep=0)

def build_one(compose, args, cnt):
    if 'build' not in cnt: return
    if getattr(args, 'if_not_exists', None):
        try: img_id = compose.podman.output([], 'inspect', ['-t', 'image', '-f', '{{.Id}}', cnt["image"]])
        except subprocess.CalledProcessError: img_id = None
        if img_id: return
    build_desc = cnt['build']
    if not hasattr(build_desc, 'items'):
        build_desc = dict(context=build_desc)
    ctx = build_desc.get('context', '.')
    dockerfile = build_desc.get("dockerfile", None)
    if dockerfile:
        dockerfile = os.path.join(ctx, dockerfile)
    else:
        dockerfile_alts = [
            'Containerfile', 'ContainerFile', 'containerfile',
            'Dockerfile', 'DockerFile','dockerfile',
        ]
        for dockerfile in dockerfile_alts:
            dockerfile = os.path.join(ctx, dockerfile)
            if os.path.exists(dockerfile): break
    if not os.path.exists(dockerfile):
        raise OSError("Dockerfile not found in "+ctx)
    build_args = ["-t", cnt["image"], "-f", dockerfile]
    if "target" in build_desc:
        build_args.extend(["--target", build_desc["target"]])
    container_to_ulimit_args(cnt, build_args)
    if getattr(args, 'no_cache', None):
        build_args.append("--no-cache")
    if getattr(args, 'pull_always', None): build_args.append("--pull-always")
    elif getattr(args, 'pull', None): build_args.append("--pull")
    args_list = norm_as_list(build_desc.get('args', {}))
    for build_arg in args_list + args.build_arg:
        build_args.extend(("--build-arg", build_arg,))
    build_args.append(ctx)
    compose.podman.run([], "build", build_args, sleep=0)

@cmd_run(podman_compose, 'build', 'build stack images')
def compose_build(compose, args):
    if args.services:
        container_names_by_service = compose.container_names_by_service
        for service in args.services:
            try:
                cnt = compose.container_by_name[container_names_by_service[service][0]]
            except:
                raise ValueError("unknown service: " + service)
            build_one(compose, args, cnt)
    else:
        for cnt in compose.containers:
            build_one(compose, args, cnt)

def create_pods(compose, args):
    for pod in compose.pods:
        podman_args = [
            "create",
            "--name={}".format(pod["name"]),
        ]
        #if compose.podman_version and not strverscmp_lt(compose.podman_version, "3.4.0"):
        #    podman_args.append("--infra-name={}_infra".format(pod["name"]))
        ports = pod.get("ports", None) or []
        if isinstance(ports, str):
            ports = [ports]
        for i in ports:
            podman_args.extend(['-p', str(i)])
        compose.podman.run([], "pod", podman_args)


def up_specific(compose, args):
    deps = []
    if not args.no_deps:
        for service in args.services:
            deps.extend([])
    # args.always_recreate_deps
    log("services", args.services)
    raise NotImplementedError("starting specific services is not yet implemented")

def get_excluded(compose, args):
    excluded = set()
    if args.services:
        excluded = set(compose.services)
        for service in args.services:
            excluded-= compose.services[service]['_deps']
            excluded.discard(service)
    log("** excluding: ", excluded)
    return excluded

@cmd_run(podman_compose, 'up', 'Create and start the entire stack or some of its services')
def compose_up(compose, args):
    excluded = get_excluded(compose, args)
    if not args.no_build:
        # `podman build` does not cache, so don't always build
        build_args = argparse.Namespace(
            if_not_exists=(not args.build),
            **args.__dict__)
        compose.commands['build'](compose, build_args)

    # TODO: implement check hash label for change
    if args.force_recreate:
        down_args = argparse.Namespace(**dict(args.__dict__, volumes=False))
        compose.commands['down'](compose, down_args)
    # args.no_recreate disables check for changes (which is not implemented)

    podman_command = 'run' if args.detach and not args.no_start else 'create'

    create_pods(compose, args)
    for cnt in compose.containers:
        if cnt["_service"] in excluded:
            log("** skipping: ", cnt['name'])
            continue
        podman_args = container_to_args(compose, cnt, detached=args.detach)
        subproc = compose.podman.run([], podman_command, podman_args)
        if podman_command == 'run' and subproc and subproc.returncode:
            compose.podman.run([], 'start', [cnt['name']])
    if args.no_start or args.detach or args.dry_run:
        return
    # TODO: handle already existing
    # TODO: if error creating do not enter loop
    # TODO: colors if sys.stdout.isatty()
    exit_code_from = args.__dict__.get('exit_code_from', None)
    if exit_code_from:
        args.abort_on_container_exit=True

    threads = []
    # for cnt in compose.containers:
    max_service_length=0
    for cnt in compose.containers:
        curr_length = len(cnt["_service"])
        max_service_length = curr_length if curr_length > max_service_length else max_service_length

    for i, cnt in enumerate(compose.containers):
        # Add colored service prefix to output by piping output through sed
        color_idx = i % len(compose.console_colors)
        color = compose.console_colors[color_idx]
        space_suffix=' ' * (max_service_length - len(cnt["_service"]) + 1)
        log_formatter = 's/^/{}[{}]{}|\x1B[0m\ /;'.format(color, cnt["_service"], space_suffix)
        log_formatter = ["sed", "-e", log_formatter]
        if cnt["_service"] in excluded:
            log("** skipping: ", cnt['name'])
            continue
        # TODO: remove sleep from podman.run
        obj = compose if exit_code_from == cnt['_service'] else None
        thread = Thread(target=compose.podman.run, args=[[], 'start', ['-a', cnt['name']]], kwargs={"obj":obj, "log_formatter": log_formatter}, daemon=True, name=cnt['name'])
        thread.start()
        threads.append(thread)
        time.sleep(1)
    
    while threads:
        for thread in threads:
            thread.join(timeout=1.0)
            if not thread.is_alive():
                threads.remove(thread)
                if args.abort_on_container_exit:
                    time.sleep(1)
                    exit_code = compose.exit_code if compose.exit_code is not None else -1
                    exit(exit_code)

def get_volume_names(compose, cnt):
    proj_name = compose.project_name
    basedir = compose.dirname
    srv_name = cnt['_service']
    ls = []
    for volume in cnt.get('volumes', []):
        if is_str(volume): volume = parse_short_mount(volume, basedir)
        volume = fix_mount_dict(compose, volume, proj_name, srv_name)
        mount_type = volume["type"]
        if mount_type!='volume': continue
        volume_name = (volume.get("_vol", None) or {}).get("name", None)
        ls.append(volume_name)
    return ls

@cmd_run(podman_compose, 'down', 'tear down entire stack')
def compose_down(compose, args):
    proj_name = compose.project_name
    excluded = get_excluded(compose, args)
    podman_args=[]
    timeout=getattr(args, 'timeout', None)
    if timeout is None:
        timeout = 1
    podman_args.extend(['-t', "{}".format(timeout)])
    containers = list(reversed(compose.containers))

    for cnt in containers:
        if cnt["_service"] in excluded: continue
        compose.podman.run([], "stop", [*podman_args, cnt["name"]], sleep=0)
    for cnt in containers:
        if cnt["_service"] in excluded: continue
        compose.podman.run([], "rm", [cnt["name"]], sleep=0)
    if args.volumes:
        vol_names_to_keep = set()
        for cnt in containers:
            if cnt["_service"] not in excluded: continue
            vol_names_to_keep.update(get_volume_names(compose, cnt))
        log("keep", vol_names_to_keep)
        for volume_name in compose.podman.volume_ls():
            if volume_name in vol_names_to_keep: continue
            compose.podman.run([], "volume", ["rm", volume_name])

    if excluded:
        return
    for pod in compose.pods:
        compose.podman.run([], "pod", ["rm", pod["name"]], sleep=0)

@cmd_run(podman_compose, 'ps', 'show status of containers')
def compose_ps(compose, args):
    proj_name = compose.project_name
    if args.quiet == True:
        compose.podman.run([], "ps", ["-a", "--format", "{{.ID}}", "--filter", f"label=io.podman.compose.project={proj_name}"])
    else:
        compose.podman.run([], "ps", ["-a", "--filter", f"label=io.podman.compose.project={proj_name}"])

@cmd_run(podman_compose, 'run', 'create a container similar to a service to run a one-off command')
def compose_run(compose, args):
    create_pods(compose, args)
    container_names=compose.container_names_by_service[args.service]
    container_name=container_names[0]
    cnt = dict(compose.container_by_name[container_name])
    deps = cnt["_deps"]
    if not args.no_deps:
        up_args = argparse.Namespace(**dict(args.__dict__,
               detach=True, services=deps,
               # defaults
               no_build=False, build=None, force_recreate=False, no_start=False, no_cache=False, build_arg=[],
               )
        )
        compose.commands['up'](compose, up_args)
    # adjust one-off container options
    name0 = "{}_{}_tmp{}".format(compose.project_name, args.service, random.randrange(0, 65536))
    cnt["name"] = args.name or name0
    if args.entrypoint: cnt["entrypoint"] = args.entrypoint
    if args.user: cnt["user"] = args.user
    if args.workdir: cnt["working_dir"] = args.workdir
    env = dict(cnt.get('environment', {}))
    if args.env:
        additional_env_vars = dict(map(lambda each: each.split('='), args.env))
        env.update(additional_env_vars)
        cnt['environment'] = env
    if not args.service_ports:
        for k in ("expose", "publishall", "ports"):
            try: del cnt[k]
            except KeyError: pass
    if args.volume:
        # TODO: handle volumes
        pass
    cnt['tty']=False if args.T else True
    if args.cnt_command is not None and len(args.cnt_command) > 0:
        cnt['command']=args.cnt_command
    # can't restart and --rm 
    if args.rm and 'restart' in cnt:
        del cnt['restart']
    # run podman
    podman_args = container_to_args(compose, cnt, args.detach)
    if not args.detach:
        podman_args.insert(1, '-i')
        if args.rm:
            podman_args.insert(1, '--rm')
    p = compose.podman.run([], 'run', podman_args, sleep=0)
    exit(p.returncode)

@cmd_run(podman_compose, 'exec', 'execute a command in a running container')
def compose_exec(compose, args):
    container_names=compose.container_names_by_service[args.service]
    container_name=container_names[args.index - 1]
    cnt = compose.container_by_name[container_name]
    podman_args = ['--interactive']
    if args.privileged: podman_args += ['--privileged']
    if args.user: podman_args += ['--user', args.user]
    if args.workdir: podman_args += ['--workdir', args.workdir]
    if not args.T: podman_args += ['--tty']
    env = dict(cnt.get('environment', {}))
    if args.env:
        additional_env_vars = dict(map(lambda each: each.split('='), args.env))
        env.update(additional_env_vars)
    for name, value in env.items():
        podman_args += ['--env', "%s=%s" % (name, value)]
    podman_args += [container_name]
    if args.cnt_command is not None and len(args.cnt_command) > 0:
        podman_args += args.cnt_command
    p = compose.podman.run([], 'exec', podman_args, sleep=0)
    exit(p.returncode)


def transfer_service_status(compose, args, action):
    # TODO: handle dependencies, handle creations
    container_names_by_service = compose.container_names_by_service
    if not args.services:
        args.services = container_names_by_service.keys()
    targets = []
    for service in args.services:
        if service not in container_names_by_service:
            raise ValueError("unknown service: " + service)
        targets.extend(container_names_by_service[service])
    if action in ['stop', 'restart']:
        targets = list(reversed(targets))
    podman_args=[]
    timeout=getattr(args, 'timeout', None)
    if timeout is not None:
        podman_args.extend(['-t', "{}".format(timeout)])
    for target in targets:
        compose.podman.run([], action, podman_args+[target], sleep=0)

@cmd_run(podman_compose, 'start', 'start specific services')
def compose_start(compose, args):
    transfer_service_status(compose, args, 'start')

@cmd_run(podman_compose, 'stop', 'stop specific services')
def compose_stop(compose, args):
    transfer_service_status(compose, args, 'stop')

@cmd_run(podman_compose, 'restart', 'restart specific services')
def compose_restart(compose, args):
    transfer_service_status(compose, args, 'restart')

@cmd_run(podman_compose, 'logs', 'show logs from services')
def compose_logs(compose, args):
    container_names_by_service = compose.container_names_by_service
    if not args.services and not args.latest:
        args.services = container_names_by_service.keys()
    targets = []
    for service in args.services:
        if service not in container_names_by_service:
            raise ValueError("unknown service: " + service)
        targets.extend(container_names_by_service[service])
    podman_args = []
    if args.follow:
        podman_args.append('-f')
    if args.latest:
        podman_args.append("-l")
    if args.names:
        podman_args.append('-n')
    if args.since:
        podman_args.extend(['--since', args.since])
    # the default value is to print all logs which is in podman = 0 and not
    # needed to be passed
    if args.tail and args.tail != 'all':
        podman_args.extend(['--tail', args.tail])
    if args.timestamps:
        podman_args.append('-t')
    if args.until:
        podman_args.extend(['--until', args.until])
    for target in targets:
        podman_args.append(target)
    compose.podman.run([], 'logs', podman_args)

@cmd_run(podman_compose, 'config', "displays the compose file")
def compose_config(compose, args):
    print(compose.merged_yaml)

###################
# command arguments parsing
###################

@cmd_parse(podman_compose, 'version')
def compose_version_parse(parser):
    parser.add_argument("-f", "--format", choices=['pretty', 'json'], default='pretty',
        help="Format the output")
    parser.add_argument("--short", action='store_true', 
        help="Shows only Podman Compose's version number")

@cmd_parse(podman_compose, 'up')
def compose_up_parse(parser):
    parser.add_argument("-d", "--detach", action='store_true',
        help="Detached mode: Run container in the background, print new container name. Incompatible with --abort-on-container-exit.")
    parser.add_argument("--no-color", action='store_true',
        help="Produce monochrome output.")
    parser.add_argument("--quiet-pull", action='store_true',
        help="Pull without printing progress information.")
    parser.add_argument("--no-deps", action='store_true',
        help="Don't start linked services.")
    parser.add_argument("--force-recreate", action='store_true',
        help="Recreate containers even if their configuration and image haven't changed.")
    parser.add_argument("--always-recreate-deps", action='store_true',
        help="Recreate dependent containers. Incompatible with --no-recreate.")
    parser.add_argument("--no-recreate", action='store_true',
        help="If containers already exist, don't recreate them. Incompatible with --force-recreate and -V.")
    parser.add_argument("--no-build", action='store_true',
        help="Don't build an image, even if it's missing.")
    parser.add_argument("--no-start", action='store_true',
        help="Don't start the services after creating them.")
    parser.add_argument("--build", action='store_true',
        help="Build images before starting containers.")
    parser.add_argument("--abort-on-container-exit", action='store_true',
        help="Stops all containers if any container was stopped. Incompatible with -d.")
    parser.add_argument("-t", "--timeout", type=float, default=10,
        help="Use this timeout in seconds for container shutdown when attached or when containers are already running. (default: 10)")
    parser.add_argument("-V", "--renew-anon-volumes", action='store_true',
        help="Recreate anonymous volumes instead of retrieving data from the previous containers.")
    parser.add_argument("--remove-orphans", action='store_true',
        help="Remove containers for services not defined in the Compose file.")
    parser.add_argument('--scale', metavar="SERVICE=NUM", action='append',
        help="Scale SERVICE to NUM instances. Overrides the `scale` setting in the Compose file if present.")
    parser.add_argument("--exit-code-from", metavar='SERVICE', type=str, default=None,
        help="Return the exit code of the selected service container. Implies --abort-on-container-exit.")

@cmd_parse(podman_compose, 'down')
def compose_down_parse(parser):
    parser.add_argument("-v", "--volumes", action='store_true', default=False,
        help="Remove named volumes declared in the `volumes` section of the Compose file and "
             "anonymous volumes attached to containers.")

@cmd_parse(podman_compose, 'run')
def compose_run_parse(parser):
    parser.add_argument("-d", "--detach", action='store_true',
        help="Detached mode: Run container in the background, print new container name.")
    parser.add_argument("--name", type=str, default=None,
        help="Assign a name to the container")
    parser.add_argument("--entrypoint", type=str, default=None,
        help="Override the entrypoint of the image.")
    parser.add_argument('-e',  '--env', metavar="KEY=VAL", action='append',
        help="Set an environment variable (can be used multiple times)")
    parser.add_argument('-l', '--label', metavar="KEY=VAL", action='append',
        help="Add or override a label (can be used multiple times)")
    parser.add_argument("-u", "--user", type=str, default=None,
        help="Run as specified username or uid")
    parser.add_argument("--no-deps", action='store_true',
        help="Don't start linked services")
    parser.add_argument("--rm", action='store_true',
        help="Remove container after run. Ignored in detached mode.")
    parser.add_argument('-p', '--publish', action='append',
        help="Publish a container's port(s) to the host (can be used multiple times)")
    parser.add_argument("--service-ports", action='store_true',
        help="Run command with the service's ports enabled and mapped to the host.")
    parser.add_argument('-v', '--volume', action='append',
        help="Bind mount a volume (can be used multiple times)")
    parser.add_argument("-T", action='store_true',
        help="Disable pseudo-tty allocation. By default `podman-compose run` allocates a TTY.")
    parser.add_argument("-w", "--workdir", type=str, default=None,
        help="Working directory inside the container")
    parser.add_argument('service', metavar='service', nargs=None,
        help='service name')
    parser.add_argument('cnt_command', metavar='command', nargs=argparse.REMAINDER,
        help='command and its arguments')

@cmd_parse(podman_compose, 'exec')
def compose_run_parse(parser):
    parser.add_argument("-d", "--detach", action='store_true',
        help="Detached mode: Run container in the background, print new container name.")
    parser.add_argument("--privileged", action='store_true', default=False,
        help="Give the process extended Linux capabilities inside the container")
    parser.add_argument("-u", "--user", type=str, default=None,
        help="Run as specified username or uid")
    parser.add_argument("-T", action='store_true',
        help="Disable pseudo-tty allocation. By default `podman-compose run` allocates a TTY.")
    parser.add_argument("--index", type=int, default=1,
        help="Index of the container if there are multiple instances of a service")
    parser.add_argument('-e', '--env', metavar="KEY=VAL", action='append',
        help="Set an environment variable (can be used multiple times)")
    parser.add_argument("-w", "--workdir", type=str, default=None,
        help="Working directory inside the container")
    parser.add_argument('service', metavar='service', nargs=None,
        help='service name')
    parser.add_argument('cnt_command', metavar='command', nargs=argparse.REMAINDER,
        help='command and its arguments')


@cmd_parse(podman_compose, ['down', 'stop', 'restart'])
def compose_parse_timeout(parser):
    parser.add_argument("-t", "--timeout",
        help="Specify a shutdown timeout in seconds. ",
        type=int, default=10)

@cmd_parse(podman_compose, ['logs'])
def compose_logs_parse(parser):
    parser.add_argument("-f", "--follow", action='store_true',
                        help="Follow log output. The default is false")
    parser.add_argument("-l", "--latest", action='store_true',
                        help="Act on the latest container podman is aware of")
    parser.add_argument("-n", "--names", action='store_true',
                        help="Output the container name in the log")
    parser.add_argument("--since", help="Show logs since TIMESTAMP",
        type=str, default=None)
    parser.add_argument("-t", "--timestamps", action='store_true',
                        help="Show timestamps.")
    parser.add_argument("--tail",
        help="Number of lines to show from the end of the logs for each "
             "container.",
        type=str, default="all")
    parser.add_argument("--until", help="Show logs until TIMESTAMP",
        type=str, default=None)
    parser.add_argument('services', metavar='services', nargs='*', default=None,
        help='service names')

@cmd_parse(podman_compose, 'pull')
def compose_pull_parse(parser):
    parser.add_argument("--force-local", action='store_true', default=False,
        help="Also pull unprefixed images for services which have a build section")

@cmd_parse(podman_compose, 'push')
def compose_push_parse(parser):
    parser.add_argument("--ignore-push-failures", action='store_true',
        help="Push what it can and ignores images with push failures. (not implemented)")
    parser.add_argument('services', metavar='services', nargs='*',
        help='services to push')

@cmd_parse(podman_compose, 'ps')
def compose_ps_parse(parser):
    parser.add_argument("-q", "--quiet",
        help="Only display container IDs", action='store_true')

@cmd_parse(podman_compose, ['build', 'up'])
def compose_build_parse(parser):
    parser.add_argument("--pull",
        help="attempt to pull a newer version of the image", action='store_true')
    parser.add_argument("--pull-always",
        help="attempt to pull a newer version of the image, Raise an error even if the image is present locally.", action='store_true')
    parser.add_argument("--build-arg", metavar="key=val", action="append", default=[],
        help="Set build-time variables for services.")
    parser.add_argument("--no-cache",
                        help="Do not use cache when building the image.", action='store_true')

@cmd_parse(podman_compose, ['build', 'up', 'down', 'start', 'stop', 'restart'])
def compose_build_parse(parser):
    parser.add_argument('services', metavar='services', nargs='*',default=None,
                        help='affected services')

def main():
    podman_compose.run()
