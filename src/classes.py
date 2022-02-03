import argparse
import json
import os
import shlex
import subprocess
import sys
import time
import yaml

from dotenv import dotenv_values

from .helpers import (
    is_str,
    is_list,
    is_dict, 
    log, 
    norm_as_dict, 
    rec_subs, 
    norm_re, 
    norm_as_list, 
    flat_deps, 
    try_int,
    norm_ports,
    get_mnt_dict,
    tr_identity
)

###################
# podman and compose classes
###################
PODMAN_CMDS = (
    "pull", "push", "build", "inspect",
    "run", "start", "stop", "rm", "volume",
)


class Podman:
    def __init__(self, compose, podman_path='podman', dry_run=False):
        self.compose = compose
        self.podman_path = podman_path
        self.dry_run = dry_run

    def output(self, podman_args, cmd='', cmd_args=None):
        cmd_args = cmd_args or []
        xargs = self.compose.get_podman_args(cmd) if cmd else []
        cmd_ls = [self.podman_path, *podman_args, cmd] + xargs + cmd_args
        log(cmd_ls)
        return subprocess.check_output(cmd_ls)

    def run(self, podman_args, cmd='', cmd_args=None, wait=True, sleep=1, obj=None):
        if obj is not None:
            obj.exit_code = None
        cmd_args = list(map(str, cmd_args or []))
        xargs = self.compose.get_podman_args(cmd) if cmd else []
        cmd_ls = [self.podman_path, *podman_args, cmd] + xargs + cmd_args
        log(" ".join([str(i) for i in cmd_ls]))
        if self.dry_run:
            return None
        # subprocess.Popen(args, bufsize = 0, executable = None, stdin = None, stdout = None, stderr = None, preexec_fn = None, close_fds = False, shell = False, cwd = None, env = None, universal_newlines = False, startupinfo = None, creationflags = 0)
        p = subprocess.Popen(cmd_ls)
        if wait:
            exit_code = p.wait()
            log("exit code:", exit_code)
            if obj is not None:
                obj.exit_code = exit_code

        if sleep:
            time.sleep(sleep)
        return p

    def volume_ls(self, proj=None):
        if not proj:
            proj = self.compose.project_name
        output = self.output([], "volume", [
            "ls", "--noheading", "--filter", f"label=io.podman.compose.project={proj}",
            "--format", "{{.Name}}",
        ]).decode('utf-8')
        volumes = output.splitlines()
        return volumes

def normalize_service(service):
    for key in ("env_file", "security_opt", "volumes"):
        if key not in service: continue
        if is_str(service[key]): service[key]=[service[key]]
    if "security_opt" in service:
        sec_ls = service["security_opt"]
        for ix, item in enumerate(sec_ls):
            if item=="seccomp:unconfined" or item=="apparmor:unconfined":
                sec_ls[ix] = item.replace(":", "=")
    for key in ("environment", "labels"):
        if key not in service: continue
        service[key] = norm_as_dict(service[key])
    if "extends" in service:
        extends = service["extends"]
        if is_str(extends):
            extends = {"service": extends}
            service["extends"] = extends
    return service

def normalize(compose):
    """
    convert compose dict of some keys from string or dicts into arrays
    """
    services = compose.get("services", None) or {}
    for service_name, service in services.items():
        normalize_service(service)
    return compose

def rec_merge_one(target, source):
    """
    update target from source recursively
    """
    done = set()
    for key, value in source.items():
        if key in target: continue
        target[key]=value
        done.add(key)
    for key, value in target.items():
        if key in done: continue
        if key not in source: continue
        value2 = source[key]
        if type(value2)!=type(value):
            raise ValueError("can't merge value of {} of type {} and {}".format(key, type(value), type(value2)))
        if is_list(value2):
            if key == 'volumes':
                # clean duplicate mount targets
                pts = set([ v.split(':', 1)[1] for v in value2 if ":" in v ])
                del_ls = [ ix for (ix, v) in enumerate(value) if ":" in v and v.split(':', 1)[1] in pts ]
                for ix in reversed(del_ls):
                    del value[ix]
                value.extend(value2)
            else:
                value.extend(value2)
        elif is_dict(value2):
            rec_merge_one(value, value2)
        else:
            target[key]=value2
    return target

def rec_merge(target, *sources):
    """
    update target recursively from sources
    """
    for source in sources:
        ret = rec_merge_one(target, source)
    return ret

def resolve_extends(services, service_names, environ):
    for name in service_names:
        service = services[name]
        ext = service.get("extends", {})
        if is_str(ext): ext = {"service": ext}
        from_service_name = ext.get("service", None)
        if not from_service_name: continue
        filename = ext.get("file", None)
        if filename:
            with open(filename, 'r') as f:
                content = yaml.safe_load(f) or {}
            if "services" in content:
                content = content["services"]
            content = rec_subs(content, environ)
            from_service = content.get(from_service_name, {})
            normalize_service(from_service)
        else:
            from_service = services.get(from_service_name, {}).copy()
            del from_service["_deps"]
            try:
                del from_service["extends"]
            except KeyError:
                pass
        new_service = rec_merge({}, from_service, service)
        services[name] = new_service

def dotenv_to_dict(dotenv_path):
    if not os.path.isfile(dotenv_path):
        return {}
    return dotenv_values(dotenv_path)

COMPOSE_DEFAULT_LS = [
    "compose.yaml",
    "compose.yml",
    "compose.override.yaml",
    "compose.override.yml",
    "podman-compose.yaml",
    "podman-compose.yml",
    "docker-compose.yml",
    "docker-compose.yaml",
    "docker-compose.override.yml",
    "docker-compose.override.yaml",
    "container-compose.yml",
    "container-compose.yaml",
    "container-compose.override.yml",
    "container-compose.override.yaml",
]

class PodmanCompose:
    def __init__(self):
        self.podman_version = None
        self.exit_code = None
        self.commands = {}
        self.global_args = None
        self.project_name = None
        self.dirname = None
        self.pods = None
        self.containers = None
        self.vols = None
        self.networks = {}
        self.default_net = "default"
        self.declared_secrets = None
        self.container_names_by_service = None
        self.container_by_name = None
        self._prefer_volume_over_mount = True

    def get_podman_args(self, cmd):
        xargs = []
        for args in self.global_args.podman_args:
            xargs.extend(shlex.split(args))
        cmd_norm = cmd if cmd != 'create' else 'run'
        cmd_args = self.global_args.__dict__.get(f"podman_{cmd_norm}_args", None) or []
        for args in cmd_args:
            xargs.extend(shlex.split(args))
        return xargs

    def run(self):
        args = self._parse_args()
        podman_path = args.podman_path
        if podman_path != 'podman':
            if os.path.isfile(podman_path) and os.access(podman_path, os.X_OK):
                podman_path = os.path.realpath(podman_path)
            else:
                # this also works if podman hasn't been installed now
                if args.dry_run == False:
                    sys.stderr.write("Binary {} has not been found.\n".format(podman_path))
                    exit(1)
        self.podman = Podman(self, podman_path, args.dry_run)
        if not args.dry_run:
            # just to make sure podman is running
            try:
                self.podman_version = self.podman.output(["--version"], '', []).decode('utf-8').strip() or ""
                self.podman_version = (self.podman_version.split() or [""])[-1]
            except subprocess.CalledProcessError:
                self.podman_version = None
            if not self.podman_version:
                sys.stderr.write("it seems that you do not have `podman` installed\n")
                exit(1)
            log("using podman version: "+self.podman_version)
        cmd_name = args.command
        if (cmd_name != "version"):
            self._parse_compose_file()
        cmd = self.commands[cmd_name]
        cmd(self, args)

    def _parse_compose_file(self):
        args = self.global_args
        cmd = args.command
        pathsep = os.environ.get("COMPOSE_PATH_SEPARATOR", None) or os.pathsep
        if not args.file:
            default_str = os.environ.get("COMPOSE_FILE", None)
            if default_str:
                default_ls = default_str.split(pathsep)
            else:
                default_ls = COMPOSE_DEFAULT_LS
            args.file = list(filter(os.path.exists, default_ls))
        files = args.file
        if not files:
            log("no compose.yaml, docker-compose.yml or container-compose.yml file found, pass files with -f")
            exit(-1)
        ex = map(os.path.exists, files)
        missing = [ fn0 for ex0, fn0 in zip(ex, files) if not ex0 ]
        if missing:
            log("missing files: ", missing)
            exit(1)
        # make absolute
        relative_files = files
        files = list(map(os.path.realpath, files))
        filename = files[0]
        project_name = args.project_name
        no_ansi = args.no_ansi
        no_cleanup = args.no_cleanup
        dry_run = args.dry_run
        host_env = None
        dirname = os.path.realpath(os.path.dirname(filename))
        dir_basename = os.path.basename(dirname)
        self.dirname = dirname
        # TODO: remove next line
        os.chdir(dirname)

        if not project_name:
            # More strict then actually needed for simplicity: podman requires [a-zA-Z0-9][a-zA-Z0-9_.-]*
            project_name = os.environ.get("COMPOSE_PROJECT_NAME", None) or dir_basename.lower()
            project_name = norm_re.sub('', project_name)
            if not project_name:
                raise RuntimeError("Project name [{}] normalized to empty".format(dir_basename))

        self.project_name = project_name


        dotenv_path = os.path.join(dirname, ".env")
        self.environ = dict(os.environ)
        dotenv_dict = dotenv_to_dict(dotenv_path)
        self.environ.update(dotenv_dict)
        os.environ.update({ key: value for key, value in dotenv_dict.items() if key.startswith('PODMAN_')})
        # see: https://docs.docker.com/compose/reference/envvars/
        # see: https://docs.docker.com/compose/env-file/
        self.environ.update({
            "COMPOSE_FILE": os.path.basename(filename),
            "COMPOSE_PROJECT_NAME": self.project_name,
            "COMPOSE_PATH_SEPARATOR": pathsep,
        })
        compose = {}
        for filename in files:
            with open(filename, 'r') as f:
                content = yaml.safe_load(f)
                #log(filename, json.dumps(content, indent = 2))
                if not isinstance(content, dict):
                    sys.stderr.write("Compose file does not contain a top level object: %s\n"%filename)
                    exit(1)
                content = normalize(content)
                #log(filename, json.dumps(content, indent = 2))
                content = rec_subs(content, self.environ)
                rec_merge(compose, content)
        self.merged_yaml = yaml.safe_dump(compose)
        compose['_dirname'] = dirname
        # debug mode
        if len(files)>1:
            log(" ** merged:\n", json.dumps(compose, indent = 2))
        ver = compose.get('version', None)
        services = compose.get('services', None)
        if services is None:
            services = {}
            log("WARNING: No services defined")

        # NOTE: maybe add "extends.service" to _deps at this stage
        flat_deps(services, with_extends=True)
        service_names = sorted([ (len(srv["_deps"]), name) for name, srv in services.items() ])
        service_names = [ name for _, name in service_names]
        resolve_extends(services, service_names, self.environ)
        flat_deps(services)
        service_names = sorted([ (len(srv["_deps"]), name) for name, srv in services.items() ])
        service_names = [ name for _, name in service_names]
        nets = compose.get("networks", None) or {}
        if not nets:
            nets["default"] = None
        self.networks = nets
        if len(self.networks)==1:
            self.default_net = list(nets.keys())[0]
        elif "default" in nets:
            self.default_net = "default"
        else:
            self.default_net = None
        default_net = self.default_net
        allnets = set()
        for name, srv in services.items():
            srv_nets = srv.get("networks", None) or default_net
            srv_nets = list(srv_nets.keys()) if is_dict(srv_nets) else norm_as_list(srv_nets)
            allnets.update(srv_nets)
        given_nets = set(nets.keys())
        missing_nets = given_nets - allnets
        print(given_nets, allnets)
        if len(missing_nets):
            missing_nets_str= ",".join(missing_nets)
            raise RuntimeError(f"missing networks: {missing_nets_str}")
        # volumes: [...]
        self.vols = compose.get('volumes', {})
        podman_compose_labels = [
            "io.podman.compose.config-hash=123",
            "io.podman.compose.project=" + project_name,
            "io.podman.compose.version=0.0.1",
            "com.docker.compose.project=" + project_name,
            "com.docker.compose.project.working_dir=" + dirname,
            "com.docker.compose.project.config_files=" + ','.join(relative_files),
        ]
        # other top-levels:
        # networks: {driver: ...}
        # configs: {...}
        self.declared_secrets = compose.get('secrets', {})
        given_containers = []
        container_names_by_service = {}
        self.services = services
        for service_name, service_desc in services.items():
            replicas = try_int(service_desc.get('deploy', {}).get('replicas', '1'))
            container_names_by_service[service_name] = []
            for num in range(1, replicas+1):
                name0 = "{project_name}_{service_name}_{num}".format(
                    project_name=project_name,
                    service_name=service_name,
                    num=num,
                )
                if num == 1:
                    name = service_desc.get("container_name", name0)
                else:
                    name = name0
                container_names_by_service[service_name].append(name)
                # log(service_name,service_desc)
                cnt = dict(name=name, num=num,
                           service_name=service_name, **service_desc)
                if 'image' not in cnt:
                    cnt['image'] = "{project_name}_{service_name}".format(
                        project_name=project_name,
                        service_name=service_name,
                    )
                labels = norm_as_list(cnt.get('labels', None))
                cnt["ports"] = norm_ports(cnt.get("ports", None))
                labels.extend(podman_compose_labels)
                labels.extend([
                    "com.docker.compose.container-number={}".format(num),
                    "com.docker.compose.service=" + service_name,
                ])
                cnt['labels'] = labels
                cnt['_service'] = service_name
                cnt['_project'] = project_name
                given_containers.append(cnt)
                volumes = cnt.get("volumes", None) or []
                for volume in volumes:
                    mnt_dict = get_mnt_dict(self, cnt, volume)
                    if mnt_dict.get("type", None)=="volume" and mnt_dict["source"] and mnt_dict["source"] not in self.vols:
                        vol_name = mnt_dict["source"]
                        raise RuntimeError(f"volume [{vol_name}] not defined in top level")
        self.container_names_by_service = container_names_by_service
        container_by_name = dict([(c["name"], c) for c in given_containers])
        #log("deps:", [(c["name"], c["_deps"]) for c in given_containers])
        given_containers = list(container_by_name.values())
        given_containers.sort(key=lambda c: len(c.get('_deps', None) or []))
        #log("sorted:", [c["name"] for c in given_containers])
        pods, containers = tr_identity(project_name, given_containers)
        self.pods = pods
        self.containers = containers
        self.container_by_name = dict([ (c["name"], c) for c in containers])

    def _parse_args(self):
        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter
        )
        self._init_global_parser(parser)
        subparsers = parser.add_subparsers(title='command', dest='command')
        subparser = subparsers.add_parser('help', help='show help')
        for cmd_name, cmd in self.commands.items():
            subparser = subparsers.add_parser(cmd_name, help=cmd._cmd_desc)
            for cmd_parser in cmd._parse_args:
                cmd_parser(subparser)
        self.global_args = parser.parse_args()
        if self.global_args.version:
            self.global_args.command = "version"
        if not self.global_args.command or self.global_args.command=='help':
            parser.print_help()
            exit(-1)
        return self.global_args

    def _init_global_parser(self, parser):
        parser.add_argument("-v", "--version",
                            help="show version", action='store_true')
        parser.add_argument("-f", "--file",
                            help="Specify an alternate compose file (default: docker-compose.yml)",
                            metavar='file', action='append', default=[])
        parser.add_argument("-p", "--project-name",
                            help="Specify an alternate project name (default: directory name)",
                            type=str, default=None)
        parser.add_argument("--podman-path",
                            help="Specify an alternate path to podman (default: use location in $PATH variable)",
                            type=str, default="podman")
        parser.add_argument("--podman-args",
                            help="custom global arguments to be passed to `podman`",
                            metavar='args', action='append', default=[])
        for podman_cmd in PODMAN_CMDS:
            parser.add_argument(f"--podman-{podman_cmd}-args",
                help=f"custom arguments to be passed to `podman {podman_cmd}`",
                metavar='args', action='append', default=[])
        parser.add_argument("--no-ansi",
                            help="Do not print ANSI control characters", action='store_true')
        parser.add_argument("--no-cleanup",
                            help="Do not stop and remove existing pod & containers", action='store_true')
        parser.add_argument("--dry-run",
                            help="No action; perform a simulation of commands", action='store_true')

###################
# decorators to add commands and parse options
###################
class cmd_run:
    def __init__(self, compose, cmd_name, cmd_desc):
        self.compose = compose
        self.cmd_name = cmd_name
        self.cmd_desc = cmd_desc

    def __call__(self, func):
        def wrapped(*args, **kw):
            return func(*args, **kw)
        wrapped._compose = self.compose
        wrapped._cmd_name = self.cmd_name
        wrapped._cmd_desc = self.cmd_desc
        wrapped._parse_args = []
        self.compose.commands[self.cmd_name] = wrapped
        return wrapped


class cmd_parse:
    def __init__(self, compose, cmd_names):
        self.compose = compose
        self.cmd_names = cmd_names if is_list(cmd_names) else [cmd_names]

    def __call__(self, func):
        def wrapped(*args, **kw):
            return func(*args, **kw)
        for cmd_name in self.cmd_names:
            self.compose.commands[cmd_name]._parse_args.append(wrapped)
        return wrapped