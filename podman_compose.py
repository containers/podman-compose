#! /usr/bin/python3
# -*- coding: utf-8 -*-

# https://docs.docker.com/compose/compose-file/#service-configuration-reference
# https://docs.docker.com/samples/
# https://docs.docker.com/compose/gettingstarted/
# https://docs.docker.com/compose/django/
# https://docs.docker.com/compose/wordpress/

from __future__ import print_function

import sys
import os
import argparse
import subprocess
import time
import re
import hashlib
import random

from threading import Thread

try:
    from shlex import quote as cmd_quote
except ImportError:
    from pipes import quote as cmd_quote

# import fnmatch
# fnmatch.fnmatchcase(env, "*_HOST")

import json
import yaml

__version__ = '0.1.5'

PY3 = sys.version_info[0] == 3
if PY3:
    basestring = str

# helper functions

is_str  = lambda s: isinstance(s, basestring)
is_dict = lambda d: isinstance(d, dict)
is_list = lambda l: not is_str(l) and not is_dict(l) and hasattr(l, "__iter__")
# identity filter
filteri = lambda a: filter(lambda i:i, a)

def try_int(i, fallback=None):
    try:
        return int(i)
    except ValueError:
        pass
    except TypeError:
        pass
    return fallback

dir_re = re.compile("^[~/\.]")
propagation_re=re.compile("^(?:z|Z|r?shared|r?slave|r?private)$")

# NOTE: if a named volume is used but not defined it gives
# ERROR: Named volume "so and so" is used in service "xyz" but no declaration was found in the volumes section.
# unless it's anon-volume

def parse_short_mount(mount_str, basedir):
    mount_a = mount_str.split(':')
    mount_opt_dict = {}
    mount_opt = None
    if len(mount_a)==1:
        # Just specify a path and let the Engine create a volume
        # - /var/lib/mysql
        mount_src, mount_dst=None, mount_str
    elif len(mount_a)==2:
        mount_src, mount_dst = mount_a
        # dest must start with /, otherwise it's option
        if not mount_dst.startswith('/'):
            mount_dst, mount_opt = mount_a
            mount_src = None
    elif len(mount_a)==3:
        mount_src, mount_dst, mount_opt = mount_a
    else:
        raise ValueError("could not parse mount "+mount_str)
    if mount_src and dir_re.match(mount_src):
        # Specify an absolute path mapping
        # - /opt/data:/var/lib/mysql
        # Path on the host, relative to the Compose file
        # - ./cache:/tmp/cache
        # User-relative path
        # - ~/configs:/etc/configs/:ro
        mount_type = "bind"
        # TODO: should we use os.path.realpath(basedir)?
        mount_src = os.path.join(basedir, os.path.expanduser(mount_src))
    else:
        # Named volume
        # - datavolume:/var/lib/mysql
        mount_type = "volume"
    mount_opts = filteri((mount_opt or '').split(','))
    for opt in mount_opts:
        if opt=='ro': mount_opt_dict["read_only"]=True
        elif opt=='rw': mount_opt_dict["read_only"]=False
        elif propagation_re.match(opt): mount_opt_dict["bind"]=dict(propagation=opt)
        else:
            # TODO: ignore
            raise ValueError("unknown mount option "+opt)
    return dict(type=mount_type, source=mount_src, target=mount_dst, **mount_opt_dict)

def fix_mount_dict(mount_dict, proj_name, srv_name):
    """
    in-place fix mount dictionary to:
    - add missing source
    - prefix source with proj_name
    """
    if mount_dict["type"]=="volume":
        source = mount_dict.get("source")
        # keep old source
        mount_dict["_source"] = source
        if not source:
            # missing source
            mount_dict["source"] = "_".join([
                proj_name, srv_name,
                hashlib.md5(mount_dict["target"].encode("utf-8")).hexdigest(),
            ])
        else:
            # prefix with proj_name
            mount_dict["source"] = proj_name+"_"+source
    return mount_dict

# docker and docker-compose support subset of bash variable substitution
# https://docs.docker.com/compose/compose-file/#variable-substitution
# https://docs.docker.com/compose/env-file/
# https://www.gnu.org/software/bash/manual/html_node/Shell-Parameter-Expansion.html
# $VARIABLE
# ${VARIABLE}
# ${VARIABLE:-default} default if not set or empty
# ${VARIABLE-default} default if not set
# ${VARIABLE:?err} raise error if not set or empty
# ${VARIABLE?err} raise error if not set
# $$ means $

var_re = re.compile(r'\$(\{(?:[^\s\$:\-\}]+)\}|(?:[^\s\$\{\}]+))')
var_def_re = re.compile(r'\$\{([^\s\$:\-\}]+)(:)?-([^\}]+)\}')
var_err_re = re.compile(r'\$\{([^\s\$:\-\}]+)(:)?\?([^\}]+)\}')

def dicts_get(dicts, key, fallback='', fallback_empty=False):
    """
    get the given key from any dict in dicts, trying them one by one
    if not found in any, then use fallback, if fallback is Exception raise is
    """
    value = None
    for d in dicts:
        value = d.get(key)
        if value is not None: break
    if not value:
        if fallback_empty or value is None:
            value = fallback
        if isinstance(value, Exception):
            raise value
    return value

def rec_subs(value, dicts):
    """
    do bash-like substitution in value and if list of dictionary do that recursively
    """
    if is_dict(value):
        value = dict([(k, rec_subs(v, dicts)) for k, v in value.items()])
    elif is_str(value):
        value = var_re.sub(lambda m: dicts_get(dicts, m.group(1).strip('{}')), value)
        sub_def = lambda m: dicts_get(dicts, m.group(1), m.group(3), m.group(2) == ':')
        value = var_def_re.sub(sub_def, value)
        sub_err = lambda m: dicts_get(dicts, m.group(1), RuntimeError(m.group(3)),
                                      m.group(2) == ':')
        value = var_err_re.sub(sub_err, value)
        value = value.replace('$$', '$')
    elif hasattr(value, "__iter__"):
        value = [rec_subs(i, dicts) for i in value]
    return value

def norm_as_list(src):
    """
    given a dictionary {key1:value1, key2: None} or list
    return a list of ["key1=value1", "key2"]
    """
    if src is None:
        dst = []
    elif is_dict(src):
        dst = [("{}={}".format(k, v) if v else k) for k, v in src.items()]
    elif is_list(src):
        dst = list(src)
    else:
        dst = [src]
    return dst


def norm_as_dict(src):
    """
    given a list ["key1=value1", "key2"]
    return a dictionary {key1:value1, key2: None}
    """
    if src is None:
        dst = {}
    elif is_dict(src):
        dst = dict(src)
    elif is_list(src):
        dst = [i.split("=", 1) for i in src if i]
        dst = dict([(a if len(a) == 2 else (a[0], None)) for a in dst])
    elif is_str(src):
        key, value = src.split("=", 1) if "=" in src else (src, None)
        dst = {key: value}
    else:
        raise ValueError("dictionary or iterable is expected")
    return dst

def norm_ulimit(inner_value):
    if is_dict(inner_value):
        if not inner_value.keys() & {"soft", "hard"}:
            raise ValueError("expected at least one soft or hard limit")
        soft = inner_value.get("soft", inner_value.get("hard"))
        hard = inner_value.get("hard", inner_value.get("soft"))
        return "{}:{}".format(soft, hard)
    elif is_list(inner_value): return norm_ulimit(norm_as_dict(inner_value))
    # if int or string return as is
    return inner_value


# transformation helpers

def adj_hosts(services, cnt, dst="127.0.0.1"):
    """
    adjust container cnt in-place to add hosts pointing to dst for services
    """
    common_extra_hosts = []
    for srv, cnts in services.items():
        common_extra_hosts.append("{}:{}".format(srv, dst))
        for cnt0 in cnts:
            common_extra_hosts.append("{}:{}".format(cnt0, dst))
    extra_hosts = list(cnt.get("extra_hosts", []))
    extra_hosts.extend(common_extra_hosts)
    # link aliases
    for link in cnt.get("links", []):
        a = link.strip().split(':', 1)
        if len(a) == 2:
            alias = a[1].strip()
            extra_hosts.append("{}:{}".format(alias, dst))
    cnt["extra_hosts"] = extra_hosts


def move_list(dst, containers, key):
    """
    move key (like port forwarding) from containers to dst (a pod or a infra container)
    """
    a = set(dst.get(key) or [])
    for cnt in containers:
        a0 = cnt.get(key)
        if a0:
            a.update(a0)
            del cnt[key]
    if a:
        dst[key] = list(a)


def move_port_fw(dst, containers):
    """
    move port forwarding from containers to dst (a pod or a infra container)
    """
    move_list(dst, containers, "ports")


def move_extra_hosts(dst, containers):
    """
    move port forwarding from containers to dst (a pod or a infra container)
    """
    move_list(dst, containers, "extra_hosts")


# transformations

transformations = {}


def trans(func):
    transformations[func.__name__.replace("tr_", "")] = func
    return func


@trans
def tr_identity(project_name, services, given_containers):
    containers = []
    for cnt in given_containers:
        containers.append(dict(cnt))
    return [], containers


@trans
def tr_publishall(project_name, services, given_containers):
    containers = []
    for cnt0 in given_containers:
        cnt = dict(cnt0, publishall=True)
        # adjust hosts to point to the gateway, TODO: adjust host env
        adj_hosts(services, cnt, '10.0.2.2')
        containers.append(cnt)
    return [], containers


@trans
def tr_hostnet(project_name, services, given_containers):
    containers = []
    for cnt0 in given_containers:
        cnt = dict(cnt0, network_mode="host")
        # adjust hosts to point to localhost, TODO: adjust host env
        adj_hosts(services, cnt, '127.0.0.1')
        containers.append(cnt)
    return [], containers


@trans
def tr_cntnet(project_name, services, given_containers):
    containers = []
    infra_name = project_name + "_infra"
    infra = dict(
        name=infra_name,
        image="k8s.gcr.io/pause:3.1",
    )
    for cnt0 in given_containers:
        cnt = dict(cnt0, network_mode="container:"+infra_name)
        deps = cnt.get("depends_on") or []
        deps.append(infra_name)
        cnt["depends_on"] = deps
        # adjust hosts to point to localhost, TODO: adjust host env
        adj_hosts(services, cnt, '127.0.0.1')
        if "hostname" in cnt:
            del cnt["hostname"]
        containers.append(cnt)
    move_port_fw(infra, containers)
    move_extra_hosts(infra, containers)
    containers.insert(0, infra)
    return [], containers


@trans
def tr_1pod(project_name, services, given_containers):
    """
    project_name:
    services: {service_name: ["container_name1", "..."]}, currently only one is supported
    given_containers: [{}, ...]
    """
    pod = dict(name=project_name)
    containers = []
    for cnt0 in given_containers:
        cnt = dict(cnt0, pod=project_name)
        # services can be accessed as localhost because they are on one pod
        # adjust hosts to point to localhost, TODO: adjust host env
        adj_hosts(services, cnt, '127.0.0.1')
        containers.append(cnt)
    return [pod], containers


@trans
def tr_1podfw(project_name, services, given_containers):
    pods, containers = tr_1pod(project_name, services, given_containers)
    pod = pods[0]
    move_port_fw(pod, containers)
    return pods, containers


def mount_dict_vol_to_bind(compose, mount_dict):
    """
    inspect volume to get directory
    create volume if needed
    and return mount_dict as bind of that directory
    """
    proj_name = compose.project_name
    shared_vols = compose.shared_vols
    if mount_dict["type"]!="volume": return mount_dict
    vol_name_orig = mount_dict.get("_source", None)
    vol_name = mount_dict["source"]
    print("podman volume inspect {vol_name} || podman volume create {vol_name}".format(vol_name=vol_name))
    # podman volume list --format '{{.Name}}\t{{.MountPoint}}' -f 'label=io.podman.compose.project=HERE'
    try: out = compose.podman.output(["volume", "inspect", vol_name]).decode('utf-8')
    except subprocess.CalledProcessError:
        compose.podman.output(["volume", "create", "--label", "io.podman.compose.project={}".format(proj_name), vol_name])
        out = compose.podman.output(["volume", "inspect", vol_name]).decode('utf-8')
    src = json.loads(out)[0]["mountPoint"]
    ret=dict(mount_dict, type="bind", source=src, _vol=vol_name)
    bind_prop=ret.get("bind", {}).get("propagation")
    if not bind_prop:
        if "bind" not in ret:
            ret["bind"]={}
        # if in top level volumes then it's shared bind-propagation=z
        if vol_name_orig and vol_name_orig in shared_vols:
            ret["bind"]["propagation"]="z"
        else:
            ret["bind"]["propagation"]="Z"
    try: del ret["volume"]
    except KeyError: pass
    return ret

def mount_desc_to_args(compose, mount_desc, srv_name, cnt_name):
    basedir = compose.dirname
    proj_name = compose.project_name
    shared_vols = compose.shared_vols
    if is_str(mount_desc): mount_desc=parse_short_mount(mount_desc, basedir)
    # not needed
    # podman support: podman run --rm -ti --mount type=volume,source=myvol,destination=/delme busybox
    mount_desc = mount_dict_vol_to_bind(compose, fix_mount_dict(mount_desc, proj_name, srv_name))
    mount_type = mount_desc.get("type")
    source = mount_desc.get("source")
    target = mount_desc["target"]
    opts=[]
    if mount_desc.get("bind"):
        bind_prop=mount_desc["bind"].get("propagation")
        if bind_prop: opts.append("bind-propagation={}".format(bind_prop))
    if mount_desc.get("read_only", False): opts.append("ro")
    if mount_type=='tmpfs':
        tmpfs_opts = mount_desc.get("tmpfs", {})
        tmpfs_size = tmpfs_opts.get("size")
        if tmpfs_size:
            opts.append("tmpfs-size={}".format(tmpfs_size))
        tmpfs_mode = tmpfs_opts.get("mode")
        if tmpfs_mode:
            opts.append("tmpfs-mode={}".format(tmpfs_mode))
    opts=",".join(opts)
    if mount_type=='bind':
        return "type=bind,source={source},destination={target},{opts}".format(
            source=source,
            target=target,
            opts=opts
        ).rstrip(",")
    elif mount_type=='tmpfs':
        return "type=tmpfs,destination={target},{opts}".format(
            target=target,
            opts=opts
        ).rstrip(",")
    else:
        raise ValueError("unknown mount type:"+mount_type)



def container_to_args(compose, cnt, detached=True, podman_command='run'):
    # TODO: double check -e , --add-host, -v, --read-only
    dirname = compose.dirname
    shared_vols = compose.shared_vols
    pod = cnt.get('pod') or ''
    podman_args = [
        podman_command,
        '--name={}'.format(cnt.get('name')),
    ]

    if detached:
        podman_args.append("-d")

    if pod:
        podman_args.append('--pod={}'.format(pod))
    sec = norm_as_list(cnt.get("security_opt"))
    for s in sec:
        podman_args.extend(['--security-opt', s])
    if cnt.get('read_only'):
        podman_args.append('--read-only')
    for i in cnt.get('labels', []):
        podman_args.extend(['--label', i])
    net = cnt.get("network_mode")
    if net:
        podman_args.extend(['--network', net])
    env = norm_as_list(cnt.get('environment', {}))
    for d in cnt.get('devices', []):
        podman_args.extend(['--device', d])
    for e in env:
        podman_args.extend(['-e', e])
    for i in cnt.get('env_file', []):
        i = os.path.realpath(os.path.join(dirname, i))
        podman_args.extend(['--env-file', i])
    tmpfs_ls = cnt.get('tmpfs', [])
    if is_str(tmpfs_ls): tmpfs_ls=[tmpfs_ls]
    for i in tmpfs_ls:
        podman_args.extend(['--tmpfs', i])
    for volume in cnt.get('volumes', []):
        # TODO: should we make it os.path.realpath(os.path.join(, i))?
        mount_args = mount_desc_to_args(compose, volume, cnt['_service'], cnt['name'])
        podman_args.extend(['--mount', mount_args])
    for i in cnt.get('extra_hosts', []):
        podman_args.extend(['--add-host', i])
    for i in cnt.get('expose', []):
        podman_args.extend(['--expose', i])
    if cnt.get('publishall'):
        podman_args.append('-P')
    for i in cnt.get('ports', []):
        podman_args.extend(['-p', i])
    user = cnt.get('user')
    if user is not None:
        podman_args.extend(['-u', user])
    if cnt.get('working_dir') is not None:
        podman_args.extend(['-w', cnt.get('working_dir')])
    if cnt.get('hostname'):
        podman_args.extend(['--hostname', cnt.get('hostname')])
    if cnt.get('shm_size'):
        podman_args.extend(['--shm_size', '{}'.format(cnt.get('shm_size'))])
    if cnt.get('stdin_open'):
        podman_args.append('-i')
    if cnt.get('tty'):
        podman_args.append('--tty')
    ulimit = cnt.get('ulimit', [])
    if ulimit is not None:
        # ulimit can be a single value, i.e. ulimit: host
        if is_str(ulimit):
            podman_args.extend(['--ulimit', ulimit])
        # or a dictionary or list:
        else:
            ulimit = norm_as_dict(ulimit)
            ulimit = [ "{}={}".format(ulimit_key, norm_ulimit(inner_value)) for ulimit_key, inner_value in ulimit.items()]
            for i in ulimit:
                podman_args.extend(['--ulimit', i])
    # currently podman shipped by fedora does not package this
    # if cnt.get('init'):
    #    args.append('--init')
    entrypoint = cnt.get('entrypoint')
    if entrypoint is not None:
        if is_str(entrypoint):
            podman_args.extend(['--entrypoint', entrypoint])
        else:
            podman_args.extend(['--entrypoint', json.dumps(entrypoint)])

    # WIP: healthchecks are still work in progress
    healthcheck = cnt.get('healthcheck', None) or {}
    if not is_dict(healthcheck):
        raise ValueError("'healthcheck' must be an key-value mapping")
    healthcheck_test = healthcheck.get('test')
    if healthcheck_test:
        # If it's a string, it's equivalent to specifying CMD-SHELL
        if is_str(healthcheck_test):
            # podman does not add shell to handle command with whitespace
            podman_args.extend(['--healthcheck-command', '/bin/sh -c {}'.format(cmd_quote(healthcheck_test))])
        elif is_list(healthcheck_test):
            # If it's a list, first item is either NONE, CMD or CMD-SHELL.
            healthcheck_type = healthcheck_test.pop(0)
            if healthcheck_type == 'NONE':
                podman_args.append("--no-healthcheck")
            elif healthcheck_type == 'CMD':
                podman_args.extend(['--healthcheck-command', '/bin/sh -c {}'.format(
                    "' '".join([cmd_quote(i) for i in healthcheck_test])
                )])
            elif healthcheck_type == 'CMD-SHELL':
                if len(healthcheck_test)!=1:
                    raise ValueError("'CMD_SHELL' takes a single string after it")
                podman_args.extend(['--healthcheck-command', '/bin/sh -c {}'.format(cmd_quote(healthcheck_test[0]))])
            else:
                raise ValueError(
                    "unknown healthcheck test type [{}],\
                     expecting NONE, CMD or CMD-SHELL."
                     .format(healthcheck_type)
                )
        else:
            raise ValueError("'healthcheck.test' either a string or a list")

    # interval, timeout and start_period are specified as durations.
    if 'interval' in healthcheck:
        podman_args.extend(['--healthcheck-interval', healthcheck['interval']])
    if 'timeout' in healthcheck:
        podman_args.extend(['--healthcheck-timeout', healthcheck['timeout']])
    if 'start_period' in healthcheck:
        podman_args.extend(['--healthcheck-start-period', healthcheck['start_period']])

    # convert other parameters to string
    if 'retries' in healthcheck:
        podman_args.extend(['--healthcheck-retries', '{}'.format(healthcheck['retries'])])

    podman_args.append(cnt.get('image'))  # command, ..etc.
    command = cnt.get('command')
    if command is not None:
        if is_str(command):
            podman_args.extend(command.split())
        else:
            podman_args.extend(command)
    return podman_args


def rec_deps(services, container_by_name, cnt, init_service):
    deps = cnt["_deps"]
    for dep in deps.copy():
        dep_cnts = services.get(dep)
        if not dep_cnts:
            continue
        dep_cnt = container_by_name.get(dep_cnts[0])
        if dep_cnt:
            # TODO: avoid creating loops, A->B->A
            if init_service and init_service in dep_cnt["_deps"]:
                continue
            new_deps = rec_deps(services, container_by_name,
                                dep_cnt, init_service)
            deps.update(new_deps)
    return deps


def flat_deps(services, container_by_name):
    for name, cnt in container_by_name.items():
        deps = set([(c.split(":")[0] if ":" in c else c)
                    for c in cnt.get("links", [])])
        deps.update(cnt.get("depends_on", []))
        cnt["_deps"] = deps
    for name, cnt in container_by_name.items():
        rec_deps(services, container_by_name, cnt, cnt.get('_service'))

###################
# podman and compose classes
###################

class Podman:
    def __init__(self, compose, podman_path='podman', dry_run=False):
        self.compose = compose
        self.podman_path = podman_path
        self.dry_run = dry_run
    
    def output(self, podman_args):
        cmd = [self.podman_path]+podman_args
        return subprocess.check_output(cmd)

    def run(self, podman_args, wait=True, sleep=1):
        podman_args_str = [str(arg) for arg in podman_args]
        print("podman " + " ".join(podman_args_str))
        if self.dry_run:
            return None
        cmd = [self.podman_path]+podman_args_str
        # subprocess.Popen(args, bufsize = 0, executable = None, stdin = None, stdout = None, stderr = None, preexec_fn = None, close_fds = False, shell = False, cwd = None, env = None, universal_newlines = False, startupinfo = None, creationflags = 0)
        p = subprocess.Popen(cmd)
        if wait:
            print(p.wait())
        if sleep:
            time.sleep(sleep)
        return p

def normalize(compose):
    """
    convert compose dict of some keys from string or dicts into arrays
    """
    services = compose.get("services", None) or {}
    for service_name, service in services.items():
        for key in ("env_file", "security_opt"):
            if key not in service: continue
            if is_str(service[key]): service[key]=[service[key]]
        for key in ("environment", "labels"):
            if key not in service: continue
            service[key] = norm_as_dict(service[key])
    return compose

def rec_merge(target, source):
    """
    update content of compose with keys from content recursively
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
        if is_str(value2):
            target[key]=value2
        elif is_list(value2):
            value.extend(value2)
        elif is_dict(value2):
            rec_merge(value, value2)
        else:
            raise ValueError("unexpected type of {}".format(key))
    return target

class PodmanCompose:
    def __init__(self):
        self.commands = {}
        self.global_args = None
        self.project_name = None
        self.dirname = None
        self.pods = None
        self.containers = None
        self.shared_vols = None
        self.container_names_by_service = None
        self.container_by_name = None

    def run(self):
        args = self._parse_args()
        self._parse_compose_file()
        podman_path = args.podman_path
        if podman_path != 'podman':
            if os.path.isfile(podman_path) and os.access(podman_path, os.X_OK):
                podman_path = os.path.realpath(podman_path)
            else:
                # this also works if podman hasn't been installed now
                if dry_run == False:
                    raise IOError(
                        "Binary {} has not been found.".format(podman_path))

        self.podman = Podman(self, podman_path, args.dry_run)
        cmd_name = args.command
        cmd = self.commands[cmd_name]
        cmd(self, args)

    def _parse_compose_file(self):
        args = self.global_args
        cmd = args.command
        if not args.file:
            args.file = list(filter(os.path.exists, [
                "docker-compose.yml",
                "docker-compose.yaml",
                "docker-compose.override.yml",
                "docker-compose.override.yaml",
                "container-compose.yml",
                "container-compose.yaml",
                "container-compose.override.yml",
                "container-compose.override.yaml"
            ]))
        files = args.file
        if not files:
            print("no docker-compose.yml or container-compose.yml file found, pass files with -f")
        ex = map(os.path.exists, files)
        missing = [ fn0 for ex0, fn0 in zip(ex, files) if not ex0 ]
        if missing:
            print("missing files: ", missing)
            exit(1)
        # make absolute
        files = list(map(os.path.realpath, files))
        filename = files[0]
        project_name = args.project_name
        no_ansi = args.no_ansi
        no_cleanup = args.no_cleanup
        dry_run = args.dry_run
        transform_policy = args.transform_policy
        host_env = None
        dirname = os.path.dirname(filename)
        dir_basename = os.path.basename(dirname)
        self.dirname = dirname
        # TODO: remove next line
        os.chdir(dirname)

        if not project_name:
            project_name = dir_basename
        self.project_name = project_name
        

        dotenv_path = os.path.join(dirname, ".env")
        if os.path.exists(dotenv_path):
            with open(dotenv_path, 'r') as f:
                dotenv_ls = [l.strip() for l in f if l.strip() and not l.startswith('#')]
                dotenv_dict = dict([l.split("=", 1) for l in dotenv_ls if "=" in l])
        else:
            dotenv_dict = {}
        compose={'_dirname': dirname}
        for filename in files:
            with open(filename, 'r') as f:
                content = yaml.safe_load(f)
                #print(filename, json.dumps(content, indent = 2))
                content = normalize(content)
                #print(filename, json.dumps(content, indent = 2))
                content = rec_subs(content, [os.environ, dotenv_dict])
                rec_merge(compose, content)
        # debug mode
        if len(files)>1:
            print(" ** merged:\n", json.dumps(compose, indent = 2))
        ver = compose.get('version')
        services = compose.get('services')
        # volumes: [...]
        shared_vols = compose.get('volumes', {})
        # shared_vols = list(shared_vols.keys())
        shared_vols = set(shared_vols.keys())
        self.shared_vols = shared_vols
        podman_compose_labels = [
            "io.podman.compose.config-hash=123",
            "io.podman.compose.project=" + project_name,
            "io.podman.compose.version=0.0.1",
        ]
        # other top-levels:
        # networks: {driver: ...}
        # configs: {...}
        # secrets: {...}
        given_containers = []
        container_names_by_service = {}
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
                # print(service_name,service_desc)
                cnt = dict(name=name, num=num,
                           service_name=service_name, **service_desc)
                if 'image' not in cnt:
                    cnt['image'] = "{project_name}_{service_name}".format(
                        project_name=project_name,
                        service_name=service_name,
                    )
                labels = norm_as_list(cnt.get('labels'))
                labels.extend(podman_compose_labels)
                labels.extend([
                    "com.docker.compose.container-number={}".format(num),
                    "com.docker.compose.service=" + service_name,
                ])
                cnt['labels'] = labels
                cnt['_service'] = service_name
                cnt['_project'] = project_name
                given_containers.append(cnt)
        self.container_names_by_service = container_names_by_service
        container_by_name = dict([(c["name"], c) for c in given_containers])
        flat_deps(container_names_by_service, container_by_name)
        #print("deps:", [(c["name"], c["_deps"]) for c in given_containers])
        given_containers = list(container_by_name.values())
        given_containers.sort(key=lambda c: len(c.get('_deps') or []))
        #print("sorted:", [c["name"] for c in given_containers])
        tr = transformations[transform_policy]
        pods, containers = tr(
            project_name, container_names_by_service, given_containers)
        self.pods = pods
        self.containers = containers
        self.container_by_name = dict([ (c["name"], c) for c in containers])


    def _parse_args(self):
        parser = argparse.ArgumentParser()
        self._init_global_parser(parser)
        subparsers = parser.add_subparsers(title='command', dest='command')
        subparser = subparsers.add_parser('help', help='show help')
        for cmd_name, cmd in self.commands.items():
            subparser = subparsers.add_parser(cmd_name, help=cmd._cmd_desc)
            for cmd_parser in cmd._parse_args:
                cmd_parser(subparser)
        self.global_args = parser.parse_args()
        if not self.global_args.command or self.global_args.command=='help':
            parser.print_help()
            exit(-1)
        return self.global_args

    def _init_global_parser(self, parser):
        parser.add_argument("-f", "--file",
                            help="Specify an alternate compose file (default: docker-compose.yml)",
                            metavar='file', action='append', default=[])
        parser.add_argument("-p", "--project-name",
                            help="Specify an alternate project name (default: directory name)",
                            type=str, default=None)
        parser.add_argument("--podman-path",
                            help="Specify an alternate path to podman (default: use location in $PATH variable)",
                            type=str, default="podman")
        parser.add_argument("--no-ansi",
                            help="Do not print ANSI control characters", action='store_true')
        parser.add_argument("--no-cleanup",
                            help="Do not stop and remove existing pod & containers", action='store_true')
        parser.add_argument("--dry-run",
                            help="No action; perform a simulation of commands", action='store_true')
        parser.add_argument("-t", "--transform_policy",
                            help="how to translate docker compose to podman [1pod|hostnet|accurate]",
                            choices=['1pod', '1podfw', 'hostnet', 'cntnet', 'publishall', 'identity'], default='1podfw')

podman_compose = PodmanCompose()

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

###################
# actual commands
###################

@cmd_run(podman_compose, 'pull', 'pull stack images')
def compose_pull(compose, args):
    for cnt in compose.containers:
        if cnt.get('build'): continue
        compose.podman.run(["pull", cnt["image"]], sleep=0)

@cmd_run(podman_compose, 'push', 'push stack images')
def compose_push(compose, args):
    services = set(args.services)
    for cnt in compose.containers:
        if 'build' not in cnt: continue
        if services and cnt['_service'] not in services: continue
        compose.podman.run(["push", cnt["image"]], sleep=0)

def build_one(compose, args, cnt):
    if 'build' not in cnt: return
    if getattr(args, 'if_not_exists', None):
        try: img_id = compose.podman.output(['inspect', '-t', 'image', '-f', '{{.Id}}', cnt["image"]])
        except subprocess.CalledProcessError: img_id = None
        if img_id: return
    build_desc = cnt['build']
    if not hasattr(build_desc, 'items'):
        build_desc = dict(context=build_desc)
    ctx = build_desc.get('context', '.')
    dockerfile = os.path.join(ctx, build_desc.get("dockerfile", "Dockerfile"))
    if not os.path.exists(dockerfile):
        dockerfile = os.path.join(ctx, build_desc.get("dockerfile", "dockerfile"))
        if not os.path.exists(dockerfile):
            raise OSError("Dockerfile not found in "+ctx)
    build_args = [
        "build", "-t", cnt["image"],
        "-f", dockerfile
    ]
    if getattr(args, 'pull_always', None): build_args.append("--pull-always")
    elif getattr(args, 'pull', None): build_args.append("--pull")
    args_list = norm_as_list(build_desc.get('args', {}))
    for build_arg in args_list:
        build_args.extend(("--build-arg", build_arg,))
    build_args.append(ctx)
    compose.podman.run(build_args, sleep=0)

@cmd_run(podman_compose, 'build', 'build stack images')
def compose_build(compose, args):
    for cnt in compose.containers:
        build_one(compose, args, cnt)

def create_pods(compose, args):
    for pod in compose.pods:
        podman_args = [
            "pod", "create",
            "--name={}".format(pod["name"]),
            "--share", "net",
        ]
        ports = pod.get("ports") or []
        for i in ports:
            podman_args.extend(['-p', i])
        compose.podman.run(podman_args)

def up_specific(compose, args):
    deps = []
    if not args.no_deps:
        for service in args.services:
            deps.extend([])
    # args.always_recreate_deps 
    print("services", args.services)
    raise NotImplementedError("starting specific services is not yet implemented")

@cmd_run(podman_compose, 'up', 'Create and start the entire stack or some of its services')
def compose_up(compose, args):
    if args.services:
        return up_specific(compose, args)

    if not args.no_build:
        # `podman build` does not cache, so don't always build
        build_args = argparse.Namespace(
            if_not_exists=(not args.build),
            **args.__dict__,
        )
        compose.commands['build'](compose, build_args)
    
    shared_vols = compose.shared_vols
    
    # TODO: implement check hash label for change
    if args.force_recreate:
        compose.commands['down'](compose, args)
    # args.no_recreate disables check for changes (which is not implemented)

    podman_command = 'run' if args.detach and not args.no_start else 'create'

    create_pods(compose, args)
    for cnt in compose.containers:
        podman_args = container_to_args(compose, cnt,
            detached=args.detach, podman_command=podman_command)
        compose.podman.run(podman_args)
    if args.no_start or args.detach or args.dry_run: return
    # TODO: handle already existing
    # TODO: if error creating do not enter loop
    # TODO: colors if sys.stdout.isatty()

    threads = []
    for cnt in compose.containers:
        # TODO: remove sleep from podman.run
        thread = Thread(target=compose.podman.run, args=[['start', '-a', cnt['name']]], daemon=True)
        thread.start()
        threads.append(thread)
        time.sleep(1)
    while True:
        for thread in threads:
            thread.join(timeout=1.0)
            if thread.is_alive(): continue
            if args.abort_on_container_exit:
                exit(-1)

@cmd_run(podman_compose, 'down', 'tear down entire stack')
def compose_down(compose, args):
    for cnt in compose.containers:
        compose.podman.run(["stop", "-t=1", cnt["name"]], sleep=0)
    for cnt in compose.containers:
        compose.podman.run(["rm", cnt["name"]], sleep=0)
    for pod in compose.pods:
        compose.podman.run(["pod", "rm", pod["name"]], sleep=0)

@cmd_run(podman_compose, 'run', 'create a container similar to a service to run a one-off command')
def compose_run(compose, args):
    create_pods(compose, args)
    print(args)
    container_names=compose.container_names_by_service[args.service]
    container_name=container_names[0]
    cnt = compose.container_by_name[container_name]
    deps = cnt["_deps"]
    if not args.no_deps:
        # TODO: start services in deps
        pass
    # adjust one-off container options
    name0 = "{}_{}_tmp{}".format(compose.project_name, args.service, random.randrange(0, 65536))
    cnt["name"] = args.name or name0
    if args.entrypoint: cnt["entrypoint"] = args.entrypoint
    if args.user: cnt["user"] = args.user
    if args.workdir: cnt["working_dir"] = args.workdir
    if not args.service_ports:
        for k in ("expose", "publishall", "ports"):
            try: del cnt[k]
            except KeyError: pass
    if args.volume:
        # TODO: handle volumes
        pass
    cnt['tty']=False if args.T else True
    cnt['command']=args.cnt_command
    # run podman
    podman_args = container_to_args(compose, cnt, args.detach)
    if not args.detach:
        podman_args.insert(1, '-i')
        if args.rm:
            podman_args.insert(1, '--rm')
    compose.podman.run(podman_args, sleep=0)
    

def transfer_service_status(compose, args, action):
    # TODO: handle dependencies, handle creations
    container_names_by_service = compose.container_names_by_service
    targets = []
    for service in args.services:
        if service not in container_names_by_service:
            raise ValueError("unknown service: " + service)
        targets.extend(container_names_by_service[service])
    podman_args=[action]
    timeout=getattr(args, 'timeout', None)
    if timeout is not None:
        podman_args.extend(['-t', "{}".format(timeout)])
    for target in targets:
        compose.podman.run(podman_args+[target], sleep=0)

@cmd_run(podman_compose, 'start', 'start specific services')
def compose_start(compose, args):
    transfer_service_status(compose, args, 'start')

@cmd_run(podman_compose, 'stop', 'stop specific services')
def compose_stop(compose, args):
    transfer_service_status(compose, args, 'start')

@cmd_run(podman_compose, 'restart', 'restart specific services')
def compose_restart(compose, args):
    transfer_service_status(compose, args, 'restart')

###################
# command arguments parsing
###################

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
    parser.add_argument('services', metavar='SERVICES', nargs='*',
        help='service names to start')


@cmd_parse(podman_compose, 'run')
def compose_run_parse(parser):
    parser.add_argument("-d", "--detach", action='store_true',
        help="Detached mode: Run container in the background, print new container name.")
    parser.add_argument("--name", type=str, default=None,
        help="Assign a name to the container")
    parser.add_argument("--entrypoint", type=str, default=None,
        help="Override the entrypoint of the image.")
    parser.add_argument('-e', metavar="KEY=VAL", action='append',
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

@cmd_parse(podman_compose, ['stop', 'restart'])
def compose_parse_timeout(parser):
    parser.add_argument("-t", "--timeout",
        help="Specify a shutdown timeout in seconds. ",
        type=float, default=10)

@cmd_parse(podman_compose, ['start', 'stop', 'restart'])
def compose_parse_services(parser):
    parser.add_argument('services', metavar='services', nargs='+',
        help='affected services')

@cmd_parse(podman_compose, 'push')
def compose_push_parse(parser):
    parser.add_argument("--ignore-push-failures", action='store_true',
        help="Push what it can and ignores images with push failures. (not implemented)")
    parser.add_argument('services', metavar='services', nargs='*',
        help='services to push')


@cmd_parse(podman_compose, 'build')
def compose_build_parse(parser):
    parser.add_argument("--pull",
        help="attempt to pull a newer version of the image", action='store_true')
    parser.add_argument("--pull-always",
        help="attempt to pull a newer version of the image, Raise an error even if the image is present locally.", action='store_true')


def main():
    podman_compose.run()

if __name__ == "__main__":
    main()
