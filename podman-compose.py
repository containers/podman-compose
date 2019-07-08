#! /usr/bin/python3

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

try:
    from shlex import quote as cmd_quote
except ImportError:
    from pipes import quote as cmd_quote

# import fnmatch
# fnmatch.fnmatchcase(env, "*_HOST")

import json
import yaml

PY3 = sys.version_info[0] == 3
if PY3:
    basestring = str

# helper functions

is_str  = lambda s: isinstance(s, basestring)
is_dict = lambda d: isinstance(d, dict)
is_list = lambda l: not is_str(l) and not is_dict(l) and hasattr(l, "__iter__")

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
    mount_opts = filter(lambda i:i, (mount_opt or '').split(','))
    for opt in mount_opts:
        if opt=='ro': mount_opt_dict["read_only"]=True
        elif opt=='rw': mount_opt_dict["read_only"]=False
        elif propagation_re.match(opt): mount_opt_dict["bind"]=dict(propagation=opt)
        else:
            # TODO: ignore
            raise ValueError("unknown mount option "+opt)
    return dict(type=mount_type, source=mount_src, target=mount_dst, **mount_opt_dict)

def fix_mount_dict(mount_dict, srv_name, cnt_name):
    """
    in-place fix mount dictionary to add missing source
    """
    if mount_dict["type"]=="volume" and not mount_dict.get("source"):
        mount_dict["source"] = "_".join([
            srv_name, cnt_name,
            hashlib.md5(mount_dict["target"].encode("utf-8")).hexdigest(),
        ])
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
    else:
        raise ValueError("dictionary or iterable is expected")
    return dst


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


def run_podman(dry_run, podman_path, podman_args, wait=True, sleep=1):
    print("podman " + " ".join(podman_args))
    if dry_run:
        return None
    cmd = [podman_path]+podman_args
    # subprocess.Popen(args, bufsize = 0, executable = None, stdin = None, stdout = None, stderr = None, preexec_fn = None, close_fds = False, shell = False, cwd = None, env = None, universal_newlines = False, startupinfo = None, creationflags = 0)
    p = subprocess.Popen(cmd)
    if wait:
        print(p.wait())
    if sleep:
        time.sleep(sleep)
    return p

def mount_dict_vol_to_bind(mount_dict, podman_path, proj_name, shared_vols):
    """
    inspect volume to get directory
    create volume if needed
    and return mount_dict as bind of that directory
    """
    if mount_dict["type"]!="volume": return mount_dict
    vol_name = mount_dict["source"]
    print("podman volume inspect {vol_name} || podman volume create {vol_name}".format(vol_name=vol_name))
    # podman volume list --format '{{.Name}}\t{{.MountPoint}}' -f 'label=io.podman.compose.project=HERE'
    try: out = subprocess.check_output([podman_path, "volume", "inspect", vol_name])
    except subprocess.CalledProcessError:
        subprocess.check_output([podman_path, "volume", "create", "-l", "io.podman.compose.project={}".format(proj_name), vol_name])
        out = subprocess.check_output([podman_path, "volume", "inspect", vol_name])
    src = json.loads(out)[0]["mountPoint"]
    ret=dict(mount_dict, type="bind", source=src, _vol=vol_name)
    bind_prop=ret.get("bind", {}).get("propagation")
    if not bind_prop:
        if "bind" not in ret:
            ret["bind"]={}
        # if in top level volumes then it's shared bind-propagation=z
        if vol_name in shared_vols:
            ret["bind"]["propagation"]="z"
        else:
            ret["bind"]["propagation"]="Z"
    try: del ret["volume"]
    except KeyError: pass
    return ret

def mount_desc_to_args(mount_desc, podman_path, basedir, proj_name, srv_name, cnt_name, shared_vols):
    if is_str(mount_desc): mount_desc=parse_short_mount(mount_desc, basedir)
    mount_desc = mount_dict_vol_to_bind(fix_mount_dict(mount_desc, srv_name, cnt_name), podman_path, proj_name, shared_vols)
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

# pylint: disable=unused-argument
def down(project_name, dirname, pods, containers, dry_run, podman_path):
    for cnt in containers:
        run_podman(dry_run, podman_path, [
                   "stop", "-t=1", cnt["name"]], sleep=0)
    for cnt in containers:
        run_podman(dry_run, podman_path, ["rm", cnt["name"]], sleep=0)
    for pod in pods:
        run_podman(dry_run, podman_path, ["pod", "rm", pod["name"]], sleep=0)



def container_to_args(cnt, dirname, podman_path, shared_vols):
    pod = cnt.get('pod') or ''
    args = [
        'run',
        '--name={}'.format(cnt.get('name')),
        '-d'
    ]

    if pod:
        args.append('--pod={}'.format(pod))
    sec = norm_as_list(cnt.get("security_opt"))
    for s in sec:
        args.extend(['--security-opt', s])
    if cnt.get('read_only'):
        args.append('--read-only')
    for i in cnt.get('labels', []):
        args.extend(['-l', i])
    net = cnt.get("network_mode")
    if net:
        args.extend(['--network', net])
    env = norm_as_list(cnt.get('environment', {}))
    for e in env:
        args.extend(['-e', e])
    for i in cnt.get('env_file', []):
        i = os.path.realpath(os.path.join(dirname, i))
        args.extend(['--env-file', i])
    tmpfs_ls = cnt.get('tmpfs', [])
    if is_str(tmpfs_ls): tmpfs_ls=[tmpfs_ls]
    for i in tmpfs_ls:
        args.extend(['--tmpfs', i])
    for i in cnt.get('volumes', []):
        # TODO: should we make it os.path.realpath(os.path.join(, i))?
        mount_args = mount_desc_to_args(
            i, podman_path, dirname,
            cnt['_project'], cnt['_service'], cnt['name'],
            shared_vols
        )
        args.extend(['--mount', mount_args])
    for i in cnt.get('extra_hosts', []):
        args.extend(['--add-host', i])
    for i in cnt.get('expose', []):
        args.extend(['--expose', i])
    if cnt.get('publishall'):
        args.append('-P')
    for i in cnt.get('ports', []):
        args.extend(['-p', i])
    user = cnt.get('user')
    if user is not None:
        args.extend(['-u', user])
    if cnt.get('working_dir') is not None:
        args.extend(['-w', cnt.get('working_dir')])
    if cnt.get('hostname'):
        args.extend(['--hostname', cnt.get('hostname')])
    if cnt.get('shm_size'):
        args.extend(['--shm_size', '{}'.format(cnt.get('shm_size'))])
    if cnt.get('stdin_open'):
        args.append('-i')
    if cnt.get('tty'):
        args.append('--tty')
    # currently podman shipped by fedora does not package this
    # if cnt.get('init'):
    #    args.append('--init')
    entrypoint = cnt.get('entrypoint')
    if entrypoint is not None:
        if is_str(entrypoint):
            args.extend(['--entrypoint', entrypoint])
        else:
            args.extend(['--entrypoint', json.dumps(entrypoint)])

    # WIP: healthchecks are still work in progress
    healthcheck = cnt.get('healthcheck', None) or {}
    if not is_dict(healthcheck):
        raise ValueError("'healthcheck' must be an key-value mapping")
    healthcheck_test = healthcheck.get('test')
    if healthcheck_test:
        # If it’s a string, it’s equivalent to specifying CMD-SHELL
        if is_str(healthcheck_test):
            # podman does not add shell to handle command with whitespace
            args.extend(['--healthcheck-command', '/bin/sh -c {}'.format(cmd_quote(healthcheck_test))])
        elif is_list(healthcheck_test):
            # If it’s a list, first item is either NONE, CMD or CMD-SHELL.
            healthcheck_type = healthcheck_test.pop(0)
            if healthcheck_type == 'NONE':
                args.append("--no-healthcheck")
            elif healthcheck_type == 'CMD':
                args.extend(['--healthcheck-command', '/bin/sh -c {}'.format(
                    "' '".join([cmd_quote(i) for i in healthcheck_test])
                )])
            elif healthcheck_type == 'CMD-SHELL':
                if len(healthcheck_test)!=1:
                    raise ValueError("'CMD_SHELL' takes a single string after it")
                args.extend(['--healthcheck-command', '/bin/sh -c {}'.format(cmd_quote(healthcheck_test[0])]))
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
        args.extend(['--healthcheck-interval', healthcheck['interval']])
    if 'timeout' in healthcheck:
        args.extend(['--healthcheck-timeout', healthcheck['timeout']])
    if 'start_period' in healthcheck:
        args.extend(['--healthcheck-start-period', healthcheck['start_period']])

    # convert other parameters to string
    if 'retries' in healthcheck:
        args.extend(['--healthcheck-retries', '{}'.format(healthcheck['retries'])])

    args.append(cnt.get('image'))  # command, ..etc.
    command = cnt.get('command')
    if command is not None:
        if is_str(command):
            args.extend([command])
        else:
            args.extend(command)
    return args


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

# pylint: disable=unused-argument
def pull(project_name, dirname, pods, containers, dry_run, podman_path):
    for cnt in containers:
        if cnt.get('build'): continue
        run_podman(dry_run, podman_path, ["pull", cnt["image"]], sleep=0)

def push(project_name, dirname, pods, containers, dry_run, podman_path, cmd_args):
    parser = argparse.ArgumentParser()
    parser.prog+=' push'
    parser.add_argument("--ignore-push-failures", action='store_true',
        help="Push what it can and ignores images with push failures. (not implemented)")
    parser.add_argument('services', metavar='services', nargs='*',
        help='services to push')
    args = parser.parse_args(cmd_args)
    services = set(args.services)
    for cnt in containers:
        if 'build' not in cnt: continue
        if services and cnt['_service'] not in services: continue
        run_podman(dry_run, podman_path, ["push", cnt["image"]], sleep=0)

# pylint: disable=unused-argument
def build(project_name, dirname, pods, containers, dry_run, podman_path, podman_args=[]):
    for cnt in containers:
        if 'build' not in cnt: continue
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
        build_args.extend(podman_args)
        args_list = norm_as_list(build_desc.get('args', {}))
        for build_arg in args_list:
            build_args.extend(("--build-arg", build_arg,))
        build_args.append(ctx)
        run_podman(dry_run, podman_path, build_args, sleep=0)

def up(project_name, dirname, pods, containers, no_cleanup, dry_run, podman_path, shared_vols):
    os.chdir(dirname)

    # NOTE: podman does not cache, so don't always build
    # TODO: if build and the following command fails "podman inspect -t image <image_name>" then run build

    # no need remove them if they have same hash label
    if no_cleanup == False:
        down(project_name, dirname, pods, containers, dry_run, podman_path)

    for pod in pods:
        args = [
            "pod", "create",
            "--name={}".format(pod["name"]),
            "--share", "net",
        ]
        ports = pod.get("ports") or []
        for i in ports:
            args.extend(['-p', i])
        run_podman(dry_run, podman_path, args)

    for cnt in containers:
        # TODO: -e , --add-host, -v, --read-only
        args = container_to_args(cnt, dirname, podman_path, shared_vols)
        run_podman(dry_run, podman_path, args)


def run_compose(
        cmd, cmd_args, filename, project_name,
        no_ansi, no_cleanup, dry_run,
        transform_policy, podman_path, host_env=None,
    ):
    if not os.path.exists(filename):
        alt_path = filename.replace('.yml', '.yaml')
        if os.path.exists(alt_path):
            filename = alt_path
        else:
            print("file [{}] not found".format(filename))
            exit(-1)
    filename = os.path.realpath(filename)
    dirname = os.path.dirname(filename)
    dir_basename = os.path.basename(dirname)

    if podman_path != 'podman':
        if os.path.isfile(podman_path) and os.access(podman_path, os.X_OK):
            podman_path = os.path.realpath(podman_path)
        else:
            # this also works if podman hasn't been installed now
            if dry_run == False:
                raise IOError(
                    "Binary {} has not been found.".format(podman_path))

    if not project_name:
        project_name = dir_basename

    dotenv_path = os.path.join(dirname, ".env")
    if os.path.exists(dotenv_path):
        with open(dotenv_path, 'r') as f:
            dotenv_ls = [l.strip() for l in f if l.strip() and not l.startswith('#')]
            dotenv_dict = dict([l.split("=", 1) for l in dotenv_ls if "=" in l])
    else:
        dotenv_dict = {}

    with open(filename, 'r') as f:
        compose = rec_subs(yaml.safe_load(f), [os.environ, dotenv_dict])

    compose['_dirname']=dirname
    # debug mode
    #print(json.dumps(compose, indent = 2))

    ver = compose.get('version')
    services = compose.get('services')
    # volumes: [...]
    shared_vols = compose.get('volumes', {})
    # shared_vols = list(shared_vols.keys())
    shared_vols = set(shared_vols.keys())
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
    container_by_name = dict([(c["name"], c) for c in given_containers])
    flat_deps(container_names_by_service, container_by_name)
    #print("deps:", [(c["name"], c["_deps"]) for c in given_containers])
    given_containers = list(container_by_name.values())
    given_containers.sort(key=lambda c: len(c.get('_deps') or []))
    #print("sorted:", [c["name"] for c in given_containers])
    tr = transformations[transform_policy]
    pods, containers = tr(
        project_name, container_names_by_service, given_containers)
    if cmd != "build" and cmd != "push" and cmd_args:
        raise ValueError("'{}' does not accept any argument".format(cmd))
    if cmd == "pull":
        pull(project_name, dirname, pods, containers, dry_run, podman_path)
    if cmd == "push":
        push(project_name, dirname, pods, containers, dry_run, podman_path, cmd_args)
    elif cmd == "build":
        parser = argparse.ArgumentParser()
        parser.prog+=' build'
        parser.add_argument("--pull",
            help="attempt to pull a newer version of the image", action='store_true')
        parser.add_argument("--pull-always",
            help="attempt to pull a newer version of the image, Raise an error even if the image is present locally.", action='store_true')
        args = parser.parse_args(cmd_args)
        podman_args = []
        if args.pull_always: podman_args.append("--pull-always")
        elif args.pull: podman_args.append("--pull")
        build(project_name, dirname, pods, containers, dry_run, podman_path, podman_args)
    elif cmd == "up":
        up(project_name, dirname, pods, containers,
           no_cleanup, dry_run, podman_path, shared_vols)
    elif cmd == "down":
        down(project_name, dirname, pods, containers, dry_run, podman_path)
    else:
        raise NotImplementedError("command {} is not implemented".format(cmd))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', metavar='command',
                        help='command to run',
                        choices=['up', 'down', 'build', 'pull', 'push'], nargs=None, default="up")
    parser.add_argument('args', nargs=argparse.REMAINDER)
    parser.add_argument("-f", "--file",
                        help="Specify an alternate compose file (default: docker-compose.yml)",
                        type=str, default="docker-compose.yml")
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

    args = parser.parse_args()
    run_compose(
        cmd=args.command,
        cmd_args=args.args,
        filename=args.file,
        project_name=args.project_name,
        no_ansi=args.no_ansi,
        no_cleanup=args.no_cleanup,
        dry_run=args.dry_run,
        transform_policy=args.transform_policy,
        podman_path=args.podman_path
    )


if __name__ == "__main__":
    main()
