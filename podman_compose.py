#! /usr/bin/python3
# -*- coding: utf-8 -*-

# https://docs.docker.com/compose/compose-file/#service-configuration-reference
# https://docs.docker.com/samples/
# https://docs.docker.com/compose/gettingstarted/
# https://docs.docker.com/compose/django/
# https://docs.docker.com/compose/wordpress/

# TODO: podman pod logs --color -n -f pod_testlogs


import sys
import os
import getpass
import argparse
import itertools
import subprocess
import time
import re
import hashlib
import random
import json
import glob

from threading import Thread

import shlex

try:
    from shlex import quote as cmd_quote
except ImportError:
    from pipes import quote as cmd_quote

# import fnmatch
# fnmatch.fnmatchcase(env, "*_HOST")

import yaml
from dotenv import dotenv_values

__version__ = "1.0.6"

script = os.path.realpath(sys.argv[0])

# helper functions
is_str = lambda s: isinstance(s, str)
is_dict = lambda d: isinstance(d, dict)
is_list = lambda l: not is_str(l) and not is_dict(l) and hasattr(l, "__iter__")
# identity filter
filteri = lambda a: filter(lambda i: i, a)


def try_int(i, fallback=None):
    try:
        return int(i)
    except ValueError:
        pass
    except TypeError:
        pass
    return fallback


def try_float(i, fallback=None):
    try:
        return float(i)
    except ValueError:
        pass
    except TypeError:
        pass
    return fallback


def log(*msgs, sep=" ", end="\n"):
    line = (sep.join([str(msg) for msg in msgs])) + end
    sys.stderr.write(line)
    sys.stderr.flush()


dir_re = re.compile(r"^[~/\.]")
propagation_re = re.compile(
    "^(?:z|Z|O|U|r?shared|r?slave|r?private|r?unbindable|r?bind|(?:no)?(?:exec|dev|suid))$"
)
norm_re = re.compile("[^-_a-z0-9]")
num_split_re = re.compile(r"(\d+|\D+)")

PODMAN_CMDS = (
    "pull",
    "push",
    "build",
    "inspect",
    "run",
    "start",
    "stop",
    "rm",
    "volume",
)

t_re = re.compile(r"^(?:(\d+)[m:])?(?:(\d+(?:\.\d+)?)s?)?$")
STOP_GRACE_PERIOD = "10"


def str_to_seconds(txt):
    if not txt:
        return None
    if isinstance(txt, (int, float)):
        return txt
    match = t_re.match(txt.strip())
    if not match:
        return None
    mins, sec = match[1], match[2]
    mins = int(mins) if mins else 0
    sec = float(sec) if sec else 0
    # "podman stop" takes only int
    # Error: invalid argument "3.0" for "-t, --time" flag: strconv.ParseUint: parsing "3.0": invalid syntax
    return int(mins * 60.0 + sec)


def ver_as_list(a):
    return [try_int(i, i) for i in num_split_re.findall(a)]


def strverscmp_lt(a, b):
    a_ls = ver_as_list(a or "")
    b_ls = ver_as_list(b or "")
    return a_ls < b_ls


def parse_short_mount(mount_str, basedir):
    mount_a = mount_str.split(":")
    mount_opt_dict = {}
    mount_opt = None
    if len(mount_a) == 1:
        # Anonymous: Just specify a path and let the engine creates the volume
        # - /var/lib/mysql
        mount_src, mount_dst = None, mount_str
    elif len(mount_a) == 2:
        mount_src, mount_dst = mount_a
        # dest must start with / like /foo:/var/lib/mysql
        # otherwise it's option like /var/lib/mysql:rw
        if not mount_dst.startswith("/"):
            mount_dst, mount_opt = mount_a
            mount_src = None
    elif len(mount_a) == 3:
        mount_src, mount_dst, mount_opt = mount_a
    else:
        raise ValueError("could not parse mount " + mount_str)
    if mount_src and dir_re.match(mount_src):
        # Specify an absolute path mapping
        # - /opt/data:/var/lib/mysql
        # Path on the host, relative to the Compose file
        # - ./cache:/tmp/cache
        # User-relative path
        # - ~/configs:/etc/configs/:ro
        mount_type = "bind"
        mount_src = os.path.abspath(
            os.path.join(basedir, os.path.expanduser(mount_src))
        )
    else:
        # Named volume
        # - datavolume:/var/lib/mysql
        mount_type = "volume"
    mount_opts = filteri((mount_opt or "").split(","))
    propagation_opts = []
    for opt in mount_opts:
        if opt == "ro":
            mount_opt_dict["read_only"] = True
        elif opt == "rw":
            mount_opt_dict["read_only"] = False
        elif opt in ("consistent", "delegated", "cached"):
            mount_opt_dict["consistency"] = opt
        elif propagation_re.match(opt):
            propagation_opts.append(opt)
        else:
            # TODO: ignore
            raise ValueError("unknown mount option " + opt)
    mount_opt_dict["bind"] = {"propagation": ",".join(propagation_opts)}
    return {
        "type": mount_type,
        "source": mount_src,
        "target": mount_dst,
        **mount_opt_dict,
    }


# NOTE: if a named volume is used but not defined it
# gives ERROR: Named volume "abc" is used in service "xyz"
#   but no declaration was found in the volumes section.
# unless it's anonymous-volume


def fix_mount_dict(compose, mount_dict, proj_name, srv_name):
    """
    in-place fix mount dictionary to:
    - define _vol to be the corresponding top-level volume
    - if name is missing it would be source prefixed with project
    - if no source it would be generated
    """
    # if already applied nothing todo
    if "_vol" in mount_dict:
        return mount_dict
    if mount_dict["type"] == "volume":
        vols = compose.vols
        source = mount_dict.get("source", None)
        vol = (vols.get(source, None) or {}) if source else {}
        name = vol.get("name", None)
        mount_dict["_vol"] = vol
        # handle anonymouse or implied volume
        if not source:
            # missing source
            vol["name"] = "_".join(
                [
                    proj_name,
                    srv_name,
                    hashlib.sha256(mount_dict["target"].encode("utf-8")).hexdigest(),
                ]
            )
        elif not name:
            external = vol.get("external", None)
            if isinstance(external, dict):
                vol["name"] = external.get("name", f"{source}")
            elif external:
                vol["name"] = f"{source}"
            else:
                vol["name"] = f"{proj_name}_{source}"
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

var_re = re.compile(
    r"""
    \$(?:
        (?P<escaped>\$) |
        (?P<named>[_a-zA-Z][_a-zA-Z0-9]*) |
        (?:{
            (?P<braced>[_a-zA-Z][_a-zA-Z0-9]*)
            (?:(?P<empty>:)?(?:
                (?:-(?P<default>[^}]*)) |
                (?:\?(?P<err>[^}]*))
            ))?
        })
    )
""",
    re.VERBOSE,
)


def rec_subs(value, subs_dict):
    """
    do bash-like substitution in value and if list of dictionary do that recursively
    """
    if is_dict(value):
        value = {k: rec_subs(v, subs_dict) for k, v in value.items()}
    elif is_str(value):

        def convert(m):
            if m.group("escaped") is not None:
                return "$"
            name = m.group("named") or m.group("braced")
            value = subs_dict.get(name)
            if value == "" and m.group("empty"):
                value = None
            if value is not None:
                return str(value)
            if m.group("err") is not None:
                raise RuntimeError(m.group("err"))
            return m.group("default") or ""

        value = var_re.sub(convert, value)
    elif hasattr(value, "__iter__"):
        value = [rec_subs(i, subs_dict) for i in value]
    return value


def norm_as_list(src):
    """
    given a dictionary {key1:value1, key2: None} or list
    return a list of ["key1=value1", "key2"]
    """
    if src is None:
        dst = []
    elif is_dict(src):
        dst = [(f"{k}={v}" if v is not None else k) for k, v in src.items()]
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
        dst = [(a if len(a) == 2 else (a[0], None)) for a in dst]
        dst = dict(dst)
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
        soft = inner_value.get("soft", inner_value.get("hard", None))
        hard = inner_value.get("hard", inner_value.get("soft", None))
        return f"{soft}:{hard}"
    if is_list(inner_value):
        return norm_ulimit(norm_as_dict(inner_value))
    # if int or string return as is
    return inner_value


# def tr_identity(project_name, given_containers):
#    pod_name = f'pod_{project_name}'
#    pod = dict(name=pod_name)
#    containers = []
#    for cnt in given_containers:
#        containers.append(dict(cnt, pod=pod_name))
#    return [pod], containers


def transform(args, project_name, given_containers):
    if not args.in_pod:
        pod_name = None
        pods = []
    else:
        pod_name = f"pod_{project_name}"
        pod = {"name": pod_name}
        pods = [pod]
    containers = []
    for cnt in given_containers:
        containers.append(dict(cnt, pod=pod_name))
    return pods, containers


def assert_volume(compose, mount_dict):
    """
    inspect volume to get directory
    create volume if needed
    """
    vol = mount_dict.get("_vol", None)
    if mount_dict["type"] == "bind":
        basedir = os.path.realpath(compose.dirname)
        mount_src = mount_dict["source"]
        mount_src = os.path.realpath(
            os.path.join(basedir, os.path.expanduser(mount_src))
        )
        if not os.path.exists(mount_src):
            try:
                os.makedirs(mount_src, exist_ok=True)
            except OSError:
                pass
        return
    if mount_dict["type"] != "volume" or not vol or not vol.get("name", None):
        return
    proj_name = compose.project_name
    vol_name = vol["name"]
    is_ext = vol.get("external", None)
    log(f"podman volume inspect {vol_name} || podman volume create {vol_name}")
    # TODO: might move to using "volume list"
    # podman volume list --format '{{.Name}}\t{{.MountPoint}}' -f 'label=io.podman.compose.project=HERE'
    try:
        _ = compose.podman.output([], "volume", ["inspect", vol_name]).decode("utf-8")
    except subprocess.CalledProcessError as e:
        if is_ext:
            raise RuntimeError(f"External volume [{vol_name}] does not exists") from e
        labels = vol.get("labels", None) or []
        args = [
            "create",
            "--label",
            f"io.podman.compose.project={proj_name}",
            "--label",
            f"com.docker.compose.project={proj_name}",
        ]
        for item in norm_as_list(labels):
            args.extend(["--label", item])
        driver = vol.get("driver", None)
        if driver:
            args.extend(["--driver", driver])
        driver_opts = vol.get("driver_opts", None) or {}
        for opt, value in driver_opts.items():
            args.extend(["--opt", f"{opt}={value}"])
        args.append(vol_name)
        compose.podman.output([], "volume", args)
        _ = compose.podman.output([], "volume", ["inspect", vol_name]).decode("utf-8")


def mount_desc_to_mount_args(
    compose, mount_desc, srv_name, cnt_name
):  # pylint: disable=unused-argument
    mount_type = mount_desc.get("type", None)
    vol = mount_desc.get("_vol", None) if mount_type == "volume" else None
    source = vol["name"] if vol else mount_desc.get("source", None)
    target = mount_desc["target"]
    opts = []
    if mount_desc.get(mount_type, None):
        # TODO: we might need to add mount_dict[mount_type]["propagation"] = "z"
        mount_prop = mount_desc.get(mount_type, {}).get("propagation", None)
        if mount_prop:
            opts.append(f"{mount_type}-propagation={mount_prop}")
    if mount_desc.get("read_only", False):
        opts.append("ro")
    if mount_type == "tmpfs":
        tmpfs_opts = mount_desc.get("tmpfs", {})
        tmpfs_size = tmpfs_opts.get("size", None)
        if tmpfs_size:
            opts.append(f"tmpfs-size={tmpfs_size}")
        tmpfs_mode = tmpfs_opts.get("mode", None)
        if tmpfs_mode:
            opts.append(f"tmpfs-mode={tmpfs_mode}")
    opts = ",".join(opts)
    if mount_type == "bind":
        return f"type=bind,source={source},destination={target},{opts}".rstrip(",")
    if mount_type == "volume":
        return f"type=volume,source={source},destination={target},{opts}".rstrip(",")
    if mount_type == "tmpfs":
        return f"type=tmpfs,destination={target},{opts}".rstrip(",")
    raise ValueError("unknown mount type:" + mount_type)


def container_to_ulimit_args(cnt, podman_args):
    ulimit = cnt.get("ulimits", [])
    if ulimit is not None:
        # ulimit can be a single value, i.e. ulimit: host
        if is_str(ulimit):
            podman_args.extend(["--ulimit", ulimit])
        # or a dictionary or list:
        else:
            ulimit = norm_as_dict(ulimit)
            ulimit = [
                "{}={}".format(ulimit_key, norm_ulimit(inner_value))
                for ulimit_key, inner_value in ulimit.items()
            ]
            for i in ulimit:
                podman_args.extend(["--ulimit", i])


def mount_desc_to_volume_args(
    compose, mount_desc, srv_name, cnt_name
):  # pylint: disable=unused-argument
    mount_type = mount_desc["type"]
    if mount_type not in ("bind", "volume"):
        raise ValueError("unknown mount type:" + mount_type)
    vol = mount_desc.get("_vol", None) if mount_type == "volume" else None
    source = vol["name"] if vol else mount_desc.get("source", None)
    if not source:
        raise ValueError(f"missing mount source for {mount_type} on {srv_name}")
    target = mount_desc["target"]
    opts = []

    propagations = set(
        filteri(mount_desc.get(mount_type, {}).get("propagation", "").split(","))
    )
    if mount_type != "bind":
        propagations.update(
            filteri(mount_desc.get("bind", {}).get("propagation", "").split(","))
        )
    opts.extend(propagations)
    # --volume, -v[=[[SOURCE-VOLUME|HOST-DIR:]CONTAINER-DIR[:OPTIONS]]]
    # [rw|ro]
    # [z|Z]
    # [[r]shared|[r]slave|[r]private]|[r]unbindable
    # [[r]bind]
    # [noexec|exec]
    # [nodev|dev]
    # [nosuid|suid]
    # [O]
    # [U]
    read_only = mount_desc.get("read_only", None)
    if read_only is not None:
        opts.append("ro" if read_only else "rw")
    args = f"{source}:{target}"
    if opts:
        args += ":" + ",".join(opts)
    return args


def get_mnt_dict(compose, cnt, volume):
    proj_name = compose.project_name
    srv_name = cnt["_service"]
    basedir = compose.dirname
    if is_str(volume):
        volume = parse_short_mount(volume, basedir)
    return fix_mount_dict(compose, volume, proj_name, srv_name)


def get_mount_args(compose, cnt, volume):
    volume = get_mnt_dict(compose, cnt, volume)
    # proj_name = compose.project_name
    srv_name = cnt["_service"]
    mount_type = volume["type"]
    assert_volume(compose, volume)
    if compose.prefer_volume_over_mount:
        if mount_type == "tmpfs":
            # TODO: --tmpfs /tmp:rw,size=787448k,mode=1777
            args = volume["target"]
            tmpfs_opts = volume.get("tmpfs", {})
            opts = []
            size = tmpfs_opts.get("size", None)
            if size:
                opts.append(f"size={size}")
            mode = tmpfs_opts.get("mode", None)
            if mode:
                opts.append(f"mode={mode}")
            if opts:
                args += ":" + ",".join(opts)
            return ["--tmpfs", args]
        args = mount_desc_to_volume_args(compose, volume, srv_name, cnt["name"])
        return ["-v", args]
    args = mount_desc_to_mount_args(compose, volume, srv_name, cnt["name"])
    return ["--mount", args]


def get_secret_args(compose, cnt, secret):
    secret_name = secret if is_str(secret) else secret.get("source", None)
    if not secret_name or secret_name not in compose.declared_secrets.keys():
        raise ValueError(
            f'ERROR: undeclared secret: "{secret}", service: {cnt["_service"]}'
        )
    declared_secret = compose.declared_secrets[secret_name]

    source_file = declared_secret.get("file", None)
    dest_file = ""
    secret_opts = ""

    target = None if is_str(secret) else secret.get("target", None)
    uid = None if is_str(secret) else secret.get("uid", None)
    gid = None if is_str(secret) else secret.get("gid", None)
    mode = None if is_str(secret) else secret.get("mode", None)

    if source_file:
        if not target:
            dest_file = f"/run/secrets/{secret_name}"
        elif not target.startswith("/"):
            sec = target if target else secret_name
            dest_file = f"/run/secrets/{sec}"
        else:
            dest_file = target
        basedir = compose.dirname
        source_file = os.path.realpath(
            os.path.join(basedir, os.path.expanduser(source_file))
        )
        volume_ref = ["--volume", f"{source_file}:{dest_file}:ro,rprivate,rbind"]
        if uid or gid or mode:
            sec = target if target else secret_name
            log(
                f'WARNING: Service {cnt["_service"]} uses secret "{sec}" with uid, gid, or mode.'
                + " These fields are not supported by this implementation of the Compose file"
            )
        return volume_ref
    # v3.5 and up added external flag, earlier the spec
    # only required a name to be specified.
    # docker-compose does not support external secrets outside of swarm mode.
    # However accessing these via podman is trivial
    # since these commands are directly translated to
    # podman-create commands, albiet we can only support a 1:1 mapping
    # at the moment
    if declared_secret.get("external", False) or declared_secret.get("name", None):
        secret_opts += f",uid={uid}" if uid else ""
        secret_opts += f",gid={gid}" if gid else ""
        secret_opts += f",mode={mode}" if mode else ""
        # The target option is only valid for type=env,
        # which in an ideal world would work
        # for type=mount as well.
        # having a custom name for the external secret
        # has the same problem as well
        ext_name = declared_secret.get("name", None)
        err_str = 'ERROR: Custom name/target reference "{}" for mounted external secret "{}" is not supported'
        if ext_name and ext_name != secret_name:
            raise ValueError(err_str.format(secret_name, ext_name))
        if target and target != secret_name:
            raise ValueError(err_str.format(target, secret_name))
        if target:
            log(
                'WARNING: Service "{}" uses target: "{}" for secret: "{}".'.format(
                    cnt["_service"], target, secret_name
                )
                + " That is un-supported and a no-op and is ignored."
            )
        return ["--secret", "{}{}".format(secret_name, secret_opts)]

    raise ValueError(
        'ERROR: unparseable secret: "{}", service: "{}"'.format(
            secret_name, cnt["_service"]
        )
    )


def container_to_res_args(cnt, podman_args):
    # v2: https://docs.docker.com/compose/compose-file/compose-file-v2/#cpu-and-other-resources
    # cpus, cpu_shares, mem_limit, mem_reservation
    cpus_limit_v2 = try_float(cnt.get("cpus", None), None)
    cpu_shares_v2 = try_int(cnt.get("cpu_shares", None), None)
    mem_limit_v2 = cnt.get("mem_limit", None)
    mem_res_v2 = cnt.get("mem_reservation", None)
    # v3: https://docs.docker.com/compose/compose-file/compose-file-v3/#resources
    # spec: https://github.com/compose-spec/compose-spec/blob/master/deploy.md#resources
    # deploy.resources.{limits,reservations}.{cpus, memory}
    deploy = cnt.get("deploy", None) or {}
    res = deploy.get("resources", None) or {}
    limits = res.get("limits", None) or {}
    cpus_limit_v3 = try_float(limits.get("cpus", None), None)
    mem_limit_v3 = limits.get("memory", None)
    reservations = res.get("reservations", None) or {}
    # cpus_res_v3 = try_float(reservations.get('cpus', None), None)
    mem_res_v3 = reservations.get("memory", None)
    # add args
    cpus = cpus_limit_v3 or cpus_limit_v2
    if cpus:
        podman_args.extend(
            (
                "--cpus",
                str(cpus),
            )
        )
    if cpu_shares_v2:
        podman_args.extend(
            (
                "--cpu-shares",
                str(cpu_shares_v2),
            )
        )
    mem = mem_limit_v3 or mem_limit_v2
    if mem:
        podman_args.extend(
            (
                "-m",
                str(mem).lower(),
            )
        )
    mem_res = mem_res_v3 or mem_res_v2
    if mem_res:
        podman_args.extend(
            (
                "--memory-reservation",
                str(mem_res).lower(),
            )
        )


def port_dict_to_str(port_desc):
    # NOTE: `mode: host|ingress` is ignored
    cnt_port = port_desc.get("target", None)
    published = port_desc.get("published", None) or ""
    host_ip = port_desc.get("host_ip", None)
    protocol = port_desc.get("protocol", None) or "tcp"
    if not cnt_port:
        raise ValueError("target container port must be specified")
    if host_ip:
        ret = f"{host_ip}:{published}:{cnt_port}"
    else:
        ret = f"{published}:{cnt_port}" if published else f"{cnt_port}"
    if protocol != "tcp":
        ret += f"/{protocol}"
    return ret


def norm_ports(ports_in):
    if not ports_in:
        ports_in = []
    if isinstance(ports_in, str):
        ports_in = [ports_in]
    ports_out = []
    for port in ports_in:
        if isinstance(port, dict):
            port = port_dict_to_str(port)
        elif isinstance(port, int):
            port = str(port)
        elif not isinstance(port, str):
            raise TypeError("port should be either string or dict")
        ports_out.append(port)
    return ports_out


def assert_cnt_nets(compose, cnt):
    """
    create missing networks
    """
    net = cnt.get("network_mode", None)
    if net and not net.startswith("bridge"):
        return
    proj_name = compose.project_name
    nets = compose.networks
    default_net = compose.default_net
    cnt_nets = cnt.get("networks", None)
    if cnt_nets and is_dict(cnt_nets):
        cnt_nets = list(cnt_nets.keys())
    cnt_nets = norm_as_list(cnt_nets or default_net)
    for net in cnt_nets:
        net_desc = nets[net] or {}
        is_ext = net_desc.get("external", None)
        ext_desc = is_ext if is_dict(is_ext) else {}
        default_net_name = net if is_ext else f"{proj_name}_{net}"
        net_name = (
            ext_desc.get("name", None) or net_desc.get("name", None) or default_net_name
        )
        try:
            compose.podman.output([], "network", ["exists", net_name])
        except subprocess.CalledProcessError as e:
            if is_ext:
                raise RuntimeError(
                    f"External network [{net_name}] does not exists"
                ) from e
            args = [
                "create",
                "--label",
                f"io.podman.compose.project={proj_name}",
                "--label",
                f"com.docker.compose.project={proj_name}",
            ]
            # TODO: add more options here, like driver, internal, ..etc
            labels = net_desc.get("labels", None) or []
            for item in norm_as_list(labels):
                args.extend(["--label", item])
            if net_desc.get("internal", None):
                args.append("--internal")
            driver = net_desc.get("driver", None)
            if driver:
                args.extend(("--driver", driver))
            driver_opts = net_desc.get("driver_opts", None) or {}
            for key, value in driver_opts.items():
                args.extend(("--opt", f"{key}={value}"))
            ipam_config_ls = (net_desc.get("ipam", None) or {}).get(
                "config", None
            ) or []
            if is_dict(ipam_config_ls):
                ipam_config_ls = [ipam_config_ls]
            for ipam in ipam_config_ls:
                subnet = ipam.get("subnet", None)
                ip_range = ipam.get("ip_range", None)
                gateway = ipam.get("gateway", None)
                if subnet:
                    args.extend(("--subnet", subnet))
                if ip_range:
                    args.extend(("--ip-range", ip_range))
                if gateway:
                    args.extend(("--gateway", gateway))
            args.append(net_name)
            compose.podman.output([], "network", args)
            compose.podman.output([], "network", ["exists", net_name])


def get_net_args(compose, cnt):
    service_name = cnt["service_name"]
    net_args = []
    mac_address = cnt.get("mac_address", None)
    if mac_address:
        net_args.extend(["--mac-address", mac_address])
    is_bridge = False
    net = cnt.get("network_mode", None)
    if net:
        if net == "none":
            is_bridge = False
        elif net == "host":
            net_args.extend(["--network", net])
        elif net.startswith("slirp4netns:"):
            net_args.extend(["--network", net])
        elif net.startswith("service:"):
            other_srv = net.split(":", 1)[1].strip()
            other_cnt = compose.container_names_by_service[other_srv][0]
            net_args.extend(["--network", f"container:{other_cnt}"])
        elif net.startswith("container:"):
            other_cnt = net.split(":", 1)[1].strip()
            net_args.extend(["--network", f"container:{other_cnt}"])
        elif net.startswith("bridge"):
            is_bridge = True
        else:
            print(f"unknown network_mode [{net}]")
            sys.exit(1)
    else:
        is_bridge = True
    proj_name = compose.project_name
    default_net = compose.default_net
    nets = compose.networks
    cnt_nets = cnt.get("networks", None)
    aliases = [service_name]
    # NOTE: from podman manpage:
    # NOTE: A container will only have access to aliases on the first network that it joins. This is a limitation that will be removed in a later release.
    ip = None
    ip6 = None
    if cnt_nets and is_dict(cnt_nets):
        prioritized_cnt_nets = []
        # cnt_nets is {net_key: net_value, ...}
        for net_key, net_value in cnt_nets.items():
            net_value = net_value or {}
            aliases.extend(norm_as_list(net_value.get("aliases", None)))
            if not ip:
                ip = net_value.get("ipv4_address", None)
            if not ip6:
                ip6 = net_value.get("ipv6_address", None)
            net_priority = net_value.get("priority", 0)
            prioritized_cnt_nets.append(
                (
                    net_priority,
                    net_key,
                )
            )
        # sort dict by priority
        prioritized_cnt_nets.sort(reverse=True)
        cnt_nets = [net_key for _, net_key in prioritized_cnt_nets]
    cnt_nets = norm_as_list(cnt_nets or default_net)
    net_names = []
    for net in cnt_nets:
        net_desc = nets[net] or {}
        is_ext = net_desc.get("external", None)
        ext_desc = is_ext if is_dict(is_ext) else {}
        default_net_name = net if is_ext else f"{proj_name}_{net}"
        net_name = (
            ext_desc.get("name", None) or net_desc.get("name", None) or default_net_name
        )
        net_names.append(net_name)
    net_names_str = ",".join(net_names)
    if is_bridge:
        net_args.extend(["--net", net_names_str, "--network-alias", ",".join(aliases)])
    if ip:
        net_args.append(f"--ip={ip}")
    if ip6:
        net_args.append(f"--ip6={ip6}")
    return net_args


def container_to_args(compose, cnt, detached=True):
    # TODO: double check -e , --add-host, -v, --read-only
    dirname = compose.dirname
    pod = cnt.get("pod", None) or ""
    name = cnt["name"]
    podman_args = [f"--name={name}"]

    if detached:
        podman_args.append("-d")

    if pod:
        podman_args.append(f"--pod={pod}")
    deps = []
    for dep_srv in cnt.get("_deps", None) or []:
        deps.extend(compose.container_names_by_service.get(dep_srv, None) or [])
    if deps:
        deps_csv = ",".join(deps)
        podman_args.append(f"--requires={deps_csv}")
    sec = norm_as_list(cnt.get("security_opt", None))
    for sec_item in sec:
        podman_args.extend(["--security-opt", sec_item])
    ann = norm_as_list(cnt.get("annotations", None))
    for a in ann:
        podman_args.extend(["--annotation", a])
    if cnt.get("read_only", None):
        podman_args.append("--read-only")
    for i in cnt.get("labels", []):
        podman_args.extend(["--label", i])
    for c in cnt.get("cap_add", []):
        podman_args.extend(["--cap-add", c])
    for c in cnt.get("cap_drop", []):
        podman_args.extend(["--cap-drop", c])
    for item in cnt.get("group_add", []):
        podman_args.extend(["--group-add", item])
    for item in cnt.get("devices", []):
        podman_args.extend(["--device", item])
    for item in norm_as_list(cnt.get("dns", None)):
        podman_args.extend(["--dns", item])
    for item in norm_as_list(cnt.get("dns_opt", None)):
        podman_args.extend(["--dns-opt", item])
    for item in norm_as_list(cnt.get("dns_search", None)):
        podman_args.extend(["--dns-search", item])
    env_file = cnt.get("env_file", [])
    if is_str(env_file):
        env_file = [env_file]
    for i in env_file:
        i = os.path.realpath(os.path.join(dirname, i))
        podman_args.extend(["--env-file", i])
    env = norm_as_list(cnt.get("environment", {}))
    for e in env:
        podman_args.extend(["-e", e])
    tmpfs_ls = cnt.get("tmpfs", [])
    if is_str(tmpfs_ls):
        tmpfs_ls = [tmpfs_ls]
    for i in tmpfs_ls:
        podman_args.extend(["--tmpfs", i])
    for volume in cnt.get("volumes", []):
        podman_args.extend(get_mount_args(compose, cnt, volume))

    assert_cnt_nets(compose, cnt)
    podman_args.extend(get_net_args(compose, cnt))

    logging = cnt.get("logging", None)
    if logging is not None:
        podman_args.append(f'--log-driver={logging.get("driver", "k8s-file")}')
        log_opts = logging.get("options") or {}
        podman_args += [f"--log-opt={name}={value}" for name, value in log_opts.items()]
    for secret in cnt.get("secrets", []):
        podman_args.extend(get_secret_args(compose, cnt, secret))
    for i in cnt.get("extra_hosts", []):
        podman_args.extend(["--add-host", i])
    for i in cnt.get("expose", []):
        podman_args.extend(["--expose", i])
    if cnt.get("publishall", None):
        podman_args.append("-P")
    ports = cnt.get("ports", None) or []
    if isinstance(ports, str):
        ports = [ports]
    for port in ports:
        if isinstance(port, dict):
            port = port_dict_to_str(port)
        elif not isinstance(port, str):
            raise TypeError("port should be either string or dict")
        podman_args.extend(["-p", port])

    userns_mode = cnt.get("userns_mode", None)
    if userns_mode is not None:
        podman_args.extend(["--userns", userns_mode])

    user = cnt.get("user", None)
    if user is not None:
        podman_args.extend(["-u", user])
    if cnt.get("working_dir", None) is not None:
        podman_args.extend(["-w", cnt["working_dir"]])
    if cnt.get("hostname", None):
        podman_args.extend(["--hostname", cnt["hostname"]])
    if cnt.get("shm_size", None):
        podman_args.extend(["--shm-size", str(cnt["shm_size"])])
    if cnt.get("stdin_open", None):
        podman_args.append("-i")
    if cnt.get("stop_signal", None):
        podman_args.extend(["--stop-signal", cnt["stop_signal"]])
    for i in cnt.get("sysctls", []):
        podman_args.extend(["--sysctl", i])
    if cnt.get("tty", None):
        podman_args.append("--tty")
    if cnt.get("privileged", None):
        podman_args.append("--privileged")
    pull_policy = cnt.get("pull_policy", None)
    if pull_policy is not None and pull_policy != "build":
        podman_args.extend(["--pull", pull_policy])
    if cnt.get("restart", None) is not None:
        podman_args.extend(["--restart", cnt["restart"]])
    container_to_ulimit_args(cnt, podman_args)
    container_to_res_args(cnt, podman_args)
    # currently podman shipped by fedora does not package this
    if cnt.get("init", None):
        podman_args.append("--init")
    if cnt.get("init-path", None):
        podman_args.extend(["--init-path", cnt["init-path"]])
    entrypoint = cnt.get("entrypoint", None)
    if entrypoint is not None:
        if is_str(entrypoint):
            entrypoint = shlex.split(entrypoint)
        podman_args.extend(["--entrypoint", json.dumps(entrypoint)])
    platform = cnt.get("platform", None)
    if platform is not None:
        podman_args.extend(["--platform", platform])

    # WIP: healthchecks are still work in progress
    healthcheck = cnt.get("healthcheck", None) or {}
    if not is_dict(healthcheck):
        raise ValueError("'healthcheck' must be an key-value mapping")
    healthcheck_disable = healthcheck.get("disable", False)
    healthcheck_test = healthcheck.get("test", None)
    if healthcheck_disable:
        healthcheck_test = ["NONE"]
    if healthcheck_test:
        # If it's a string, it's equivalent to specifying CMD-SHELL
        if is_str(healthcheck_test):
            # podman does not add shell to handle command with whitespace
            podman_args.extend(
                ["--healthcheck-command", "/bin/sh -c " + cmd_quote(healthcheck_test)]
            )
        elif is_list(healthcheck_test):
            healthcheck_test = healthcheck_test.copy()
            # If it's a list, first item is either NONE, CMD or CMD-SHELL.
            healthcheck_type = healthcheck_test.pop(0)
            if healthcheck_type == "NONE":
                podman_args.append("--no-healthcheck")
            elif healthcheck_type == "CMD":
                cmd_q = "' '".join([cmd_quote(i) for i in healthcheck_test])
                podman_args.extend(["--healthcheck-command", "/bin/sh -c " + cmd_q])
            elif healthcheck_type == "CMD-SHELL":
                if len(healthcheck_test) != 1:
                    raise ValueError("'CMD_SHELL' takes a single string after it")
                cmd_q = cmd_quote(healthcheck_test[0])
                podman_args.extend(["--healthcheck-command", "/bin/sh -c " + cmd_q])
            else:
                raise ValueError(
                    f"unknown healthcheck test type [{healthcheck_type}],\
                     expecting NONE, CMD or CMD-SHELL."
                )
        else:
            raise ValueError("'healthcheck.test' either a string or a list")

    # interval, timeout and start_period are specified as durations.
    if "interval" in healthcheck:
        podman_args.extend(["--healthcheck-interval", healthcheck["interval"]])
    if "timeout" in healthcheck:
        podman_args.extend(["--healthcheck-timeout", healthcheck["timeout"]])
    if "start_period" in healthcheck:
        podman_args.extend(["--healthcheck-start-period", healthcheck["start_period"]])

    # convert other parameters to string
    if "retries" in healthcheck:
        podman_args.extend(["--healthcheck-retries", str(healthcheck["retries"])])

    podman_args.append(cnt["image"])  # command, ..etc.
    command = cnt.get("command", None)
    if command is not None:
        if is_str(command):
            podman_args.extend(shlex.split(command))
        else:
            podman_args.extend([str(i) for i in command])
    return podman_args


def rec_deps(services, service_name, start_point=None):
    """
    return all dependencies of service_name recursively
    """
    if not start_point:
        start_point = service_name
    deps = services[service_name]["_deps"]
    for dep_name in deps.copy():
        # avoid A depens on A
        if dep_name == service_name:
            continue
        dep_srv = services.get(dep_name, None)
        if not dep_srv:
            continue
        # NOTE: avoid creating loops, A->B->A
        if start_point and start_point in dep_srv["_deps"]:
            continue
        new_deps = rec_deps(services, dep_name, start_point)
        deps.update(new_deps)
    return deps


def flat_deps(services, with_extends=False):
    """
    create dependencies "_deps" or update it recursively for all services
    """
    for name, srv in services.items():
        deps = set()
        srv["_deps"] = deps
        if with_extends:
            ext = srv.get("extends", {}).get("service", None)
            if ext:
                if ext != name:
                    deps.add(ext)
                continue
        deps_ls = srv.get("depends_on", None) or []
        if is_str(deps_ls):
            deps_ls = [deps_ls]
        elif is_dict(deps_ls):
            deps_ls = list(deps_ls.keys())
        deps.update(deps_ls)
        # parse link to get service name and remove alias
        links_ls = srv.get("links", None) or []
        if not is_list(links_ls):
            links_ls = [links_ls]
        deps.update([(c.split(":")[0] if ":" in c else c) for c in links_ls])
    for name, srv in services.items():
        rec_deps(services, name)


###################
# podman and compose classes
###################


class Podman:
    def __init__(self, compose, podman_path="podman", dry_run=False):
        self.compose = compose
        self.podman_path = podman_path
        self.dry_run = dry_run

    def output(self, podman_args, cmd="", cmd_args=None):
        cmd_args = cmd_args or []
        xargs = self.compose.get_podman_args(cmd) if cmd else []
        cmd_ls = [self.podman_path, *podman_args, cmd] + xargs + cmd_args
        log(cmd_ls)
        return subprocess.check_output(cmd_ls)

    def exec(
        self,
        podman_args,
        cmd="",
        cmd_args=None,
    ):
        cmd_args = list(map(str, cmd_args or []))
        xargs = self.compose.get_podman_args(cmd) if cmd else []
        cmd_ls = [self.podman_path, *podman_args, cmd] + xargs + cmd_args
        log(" ".join([str(i) for i in cmd_ls]))
        os.execlp(self.podman_path, *cmd_ls)

    def run(
        self,
        podman_args,
        cmd="",
        cmd_args=None,
        wait=True,
        sleep=1,
        obj=None,
        log_formatter=None,
    ):
        if obj is not None:
            obj.exit_code = None
        cmd_args = list(map(str, cmd_args or []))
        xargs = self.compose.get_podman_args(cmd) if cmd else []
        cmd_ls = [self.podman_path, *podman_args, cmd] + xargs + cmd_args
        log(" ".join([str(i) for i in cmd_ls]))
        if self.dry_run:
            return None
        # subprocess.Popen(args, bufsize = 0, executable = None, stdin = None, stdout = None, stderr = None, preexec_fn = None, close_fds = False, shell = False, cwd = None, env = None, universal_newlines = False, startupinfo = None, creationflags = 0)
        if log_formatter is not None:
            # Pipe podman process output through log_formatter (which can add colored prefix)
            p = subprocess.Popen(
                cmd_ls, stdout=subprocess.PIPE
            )  # pylint: disable=consider-using-with
            _ = subprocess.Popen(
                log_formatter, stdin=p.stdout
            )  # pylint: disable=consider-using-with
            p.stdout.close()  # Allow p_process to receive a SIGPIPE if logging process exits.
        else:
            p = subprocess.Popen(cmd_ls)  # pylint: disable=consider-using-with

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
        output = self.output(
            [],
            "volume",
            [
                "ls",
                "--noheading",
                "--filter",
                f"label=io.podman.compose.project={proj}",
                "--format",
                "{{.Name}}",
            ],
        ).decode("utf-8")
        volumes = output.splitlines()
        return volumes


def normalize_service(service, sub_dir=""):
    # make `build.context` relative to sub_dir
    # TODO: should we make volume and secret relative too?
    if sub_dir and "build" in service:
        build = service["build"]
        context = build if is_str(build) else build.get("context", None)
        context = context or ""
        if context or sub_dir:
            if context.startswith("./"):
                context = context[2:]
            if sub_dir:
                context = os.path.join(sub_dir, context)
            context = context.rstrip("/")
            if not context:
                context = "."
            if is_str(build):
                service["build"] = context
            else:
                service["build"]["context"] = context
    for key in ("env_file", "security_opt", "volumes"):
        if key not in service:
            continue
        if is_str(service[key]):
            service[key] = [service[key]]
    if "security_opt" in service:
        sec_ls = service["security_opt"]
        for ix, item in enumerate(sec_ls):
            if item in ("seccomp:unconfined", "apparmor:unconfined"):
                sec_ls[ix] = item.replace(":", "=")
    for key in ("environment", "labels"):
        if key not in service:
            continue
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
    for service in services.values():
        normalize_service(service)
    return compose


def clone(value):
    return value.copy() if is_list(value) or is_dict(value) else value


def rec_merge_one(target, source):
    """
    update target from source recursively
    """
    done = set()
    for key, value in source.items():
        if key in target:
            continue
        target[key] = clone(value)
        done.add(key)
    for key, value in target.items():
        if key in done:
            continue
        if key not in source:
            continue
        value2 = source[key]
        if key == "command":
            target[key] = clone(value2)
            continue
        if not isinstance(value2, type(value)):
            value_type = type(value)
            value2_type = type(value2)
            raise ValueError(
                f"can't merge value of {key} of type {value_type} and {value2_type}"
            )
        if is_list(value2):
            if key == "volumes":
                # clean duplicate mount targets
                pts = {v.split(":", 1)[1] for v in value2 if ":" in v}
                del_ls = [
                    ix
                    for (ix, v) in enumerate(value)
                    if ":" in v and v.split(":", 1)[1] in pts
                ]
                for ix in reversed(del_ls):
                    del value[ix]
                value.extend(value2)
            else:
                value.extend(value2)
        elif is_dict(value2):
            rec_merge_one(value, value2)
        else:
            target[key] = value2
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
        if is_str(ext):
            ext = {"service": ext}
        from_service_name = ext.get("service", None)
        if not from_service_name:
            continue
        filename = ext.get("file", None)
        if filename:
            if filename.startswith("./"):
                filename = filename[2:]
            with open(filename, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f) or {}
            if "services" in content:
                content = content["services"]
            subdirectory = os.path.dirname(filename)
            content = rec_subs(content, environ)
            from_service = content.get(from_service_name, {})
            normalize_service(from_service, subdirectory)
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
        self.podman = None
        self.podman_version = None
        self.environ = {}
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
        self.services = None
        self.all_services = set()
        self.prefer_volume_over_mount = True
        self.merged_yaml = None
        self.yaml_hash = ""
        self.console_colors = [
            "\x1B[1;32m",
            "\x1B[1;33m",
            "\x1B[1;34m",
            "\x1B[1;35m",
            "\x1B[1;36m",
        ]

    def assert_services(self, services):
        if is_str(services):
            services = [services]
        given = set(services or [])
        missing = given - self.all_services
        if missing:
            missing_csv = ",".join(missing)
            log(f"missing services [{missing_csv}]")
            sys.exit(1)

    def get_podman_args(self, cmd):
        xargs = []
        for args in self.global_args.podman_args:
            xargs.extend(shlex.split(args))
        cmd_norm = cmd if cmd != "create" else "run"
        cmd_args = self.global_args.__dict__.get(f"podman_{cmd_norm}_args", None) or []
        for args in cmd_args:
            xargs.extend(shlex.split(args))
        return xargs

    def run(self):
        log("podman-compose version: " + __version__)
        args = self._parse_args()
        podman_path = args.podman_path
        if podman_path != "podman":
            if os.path.isfile(podman_path) and os.access(podman_path, os.X_OK):
                podman_path = os.path.realpath(podman_path)
            else:
                # this also works if podman hasn't been installed now
                if args.dry_run is False:
                    log(f"Binary {podman_path} has not been found.")
                    sys.exit(1)
        self.podman = Podman(self, podman_path, args.dry_run)
        if not args.dry_run:
            # just to make sure podman is running
            try:
                self.podman_version = (
                    self.podman.output(["--version"], "", []).decode("utf-8").strip()
                    or ""
                )
                self.podman_version = (self.podman_version.split() or [""])[-1]
            except subprocess.CalledProcessError:
                self.podman_version = None
            if not self.podman_version:
                log("it seems that you do not have `podman` installed")
                sys.exit(1)
            log("using podman version: " + self.podman_version)
        cmd_name = args.command
        compose_required = cmd_name != "version" and (
            cmd_name != "systemd" or args.action != "create-unit"
        )
        if compose_required:
            self._parse_compose_file()
        cmd = self.commands[cmd_name]
        cmd(self, args)

    def _parse_compose_file(self):
        args = self.global_args
        # cmd = args.command
        dirname = os.environ.get("COMPOSE_PROJECT_DIR", None)
        if dirname and os.path.isdir(dirname):
            os.chdir(dirname)
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
            log(
                "no compose.yaml, docker-compose.yml or container-compose.yml file found, pass files with -f"
            )
            sys.exit(-1)
        ex = map(os.path.exists, files)
        missing = [fn0 for ex0, fn0 in zip(ex, files) if not ex0]
        if missing:
            log("missing files: ", missing)
            sys.exit(1)
        # make absolute
        relative_files = files
        files = list(map(os.path.realpath, files))
        filename = files[0]
        project_name = args.project_name
        # no_ansi = args.no_ansi
        # no_cleanup = args.no_cleanup
        # dry_run = args.dry_run
        # host_env = None
        dirname = os.path.realpath(os.path.dirname(filename))
        dir_basename = os.path.basename(dirname)
        self.dirname = dirname
        # TODO: remove next line
        os.chdir(dirname)

        dotenv_path = os.path.join(dirname, args.env_file)
        dotenv_dict = dotenv_to_dict(dotenv_path)
        os.environ.update(
            {
                key: value
                for key, value in dotenv_dict.items()
                if key.startswith("PODMAN_")
            }
        )
        self.environ = dict(os.environ)
        self.environ.update(dotenv_dict)
        # see: https://docs.docker.com/compose/reference/envvars/
        # see: https://docs.docker.com/compose/env-file/
        self.environ.update(
            {
                "COMPOSE_PROJECT_DIR": dirname,
                "COMPOSE_FILE": pathsep.join(relative_files),
                "COMPOSE_PATH_SEPARATOR": pathsep,
            }
        )
        compose = {}
        for filename in files:
            with open(filename, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
                # log(filename, json.dumps(content, indent = 2))
                if not isinstance(content, dict):
                    sys.stderr.write(
                        "Compose file does not contain a top level object: %s\n"
                        % filename
                    )
                    sys.exit(1)
                content = normalize(content)
                # log(filename, json.dumps(content, indent = 2))
                content = rec_subs(content, self.environ)
                rec_merge(compose, content)
        self.merged_yaml = yaml.safe_dump(compose)
        merged_json_b = json.dumps(compose, separators=(",", ":")).encode("utf-8")
        self.yaml_hash = hashlib.sha256(merged_json_b).hexdigest()
        compose["_dirname"] = dirname
        # debug mode
        if len(files) > 1:
            log(" ** merged:\n", json.dumps(compose, indent=2))
        # ver = compose.get('version', None)

        if not project_name:
            project_name = compose.get("name", None)
            if project_name is None:
                # More strict then actually needed for simplicity: podman requires [a-zA-Z0-9][a-zA-Z0-9_.-]*
                project_name = (
                    os.environ.get("COMPOSE_PROJECT_NAME", None) or dir_basename.lower()
                )
                project_name = norm_re.sub("", project_name)
                if not project_name:
                    raise RuntimeError(
                        f"Project name [{dir_basename}] normalized to empty"
                    )

        self.project_name = project_name
        self.environ.update({"COMPOSE_PROJECT_NAME": self.project_name})

        services = compose.get("services", None)
        if services is None:
            services = {}
            log("WARNING: No services defined")

        # NOTE: maybe add "extends.service" to _deps at this stage
        flat_deps(services, with_extends=True)
        service_names = sorted(
            [(len(srv["_deps"]), name) for name, srv in services.items()]
        )
        service_names = [name for _, name in service_names]
        resolve_extends(services, service_names, self.environ)
        flat_deps(services)
        service_names = sorted(
            [(len(srv["_deps"]), name) for name, srv in services.items()]
        )
        service_names = [name for _, name in service_names]
        nets = compose.get("networks", None) or {}
        if not nets:
            nets["default"] = None
        self.networks = nets
        if len(self.networks) == 1:
            self.default_net = list(nets.keys())[0]
        elif "default" in nets:
            self.default_net = "default"
        else:
            self.default_net = None
        default_net = self.default_net
        allnets = set()
        for name, srv in services.items():
            srv_nets = srv.get("networks", None) or default_net
            srv_nets = (
                list(srv_nets.keys()) if is_dict(srv_nets) else norm_as_list(srv_nets)
            )
            allnets.update(srv_nets)
        given_nets = set(nets.keys())
        missing_nets = allnets - given_nets
        unused_nets = given_nets - allnets - set(["default"])
        if len(unused_nets):
            unused_nets_str = ",".join(unused_nets)
            log(f"WARNING: unused networks: {unused_nets_str}")
        if len(missing_nets):
            missing_nets_str = ",".join(missing_nets)
            raise RuntimeError(f"missing networks: {missing_nets_str}")
        # volumes: [...]
        self.vols = compose.get("volumes", {})
        podman_compose_labels = [
            "io.podman.compose.config-hash=" + self.yaml_hash,
            "io.podman.compose.project=" + project_name,
            "io.podman.compose.version=" + __version__,
            f"PODMAN_SYSTEMD_UNIT=podman-compose@{project_name}.service",
            "com.docker.compose.project=" + project_name,
            "com.docker.compose.project.working_dir=" + dirname,
            "com.docker.compose.project.config_files=" + ",".join(relative_files),
        ]
        # other top-levels:
        # networks: {driver: ...}
        # configs: {...}
        self.declared_secrets = compose.get("secrets", {})
        given_containers = []
        container_names_by_service = {}
        self.services = services
        for service_name, service_desc in services.items():
            replicas = try_int(service_desc.get("deploy", {}).get("replicas", "1"))
            container_names_by_service[service_name] = []
            for num in range(1, replicas + 1):
                name0 = f"{project_name}_{service_name}_{num}"
                if num == 1:
                    name = service_desc.get("container_name", name0)
                else:
                    name = name0
                container_names_by_service[service_name].append(name)
                # log(service_name,service_desc)
                cnt = {
                    "name": name,
                    "num": num,
                    "service_name": service_name,
                    **service_desc,
                }
                if "image" not in cnt:
                    cnt["image"] = f"{project_name}_{service_name}"
                labels = norm_as_list(cnt.get("labels", None))
                cnt["ports"] = norm_ports(cnt.get("ports", None))
                labels.extend(podman_compose_labels)
                labels.extend(
                    [
                        f"com.docker.compose.container-number={num}",
                        "com.docker.compose.service=" + service_name,
                    ]
                )
                cnt["labels"] = labels
                cnt["_service"] = service_name
                cnt["_project"] = project_name
                given_containers.append(cnt)
                volumes = cnt.get("volumes", None) or []
                for volume in volumes:
                    mnt_dict = get_mnt_dict(self, cnt, volume)
                    if (
                        mnt_dict.get("type", None) == "volume"
                        and mnt_dict["source"]
                        and mnt_dict["source"] not in self.vols
                    ):
                        vol_name = mnt_dict["source"]
                        raise RuntimeError(
                            f"volume [{vol_name}] not defined in top level"
                        )
        self.container_names_by_service = container_names_by_service
        self.all_services = set(container_names_by_service.keys())
        container_by_name = {c["name"]: c for c in given_containers}
        # log("deps:", [(c["name"], c["_deps"]) for c in given_containers])
        given_containers = list(container_by_name.values())
        given_containers.sort(key=lambda c: len(c.get("_deps", None) or []))
        # log("sorted:", [c["name"] for c in given_containers])
        pods, containers = transform(args, project_name, given_containers)
        self.pods = pods
        self.containers = containers
        self.container_by_name = {c["name"]: c for c in containers}

    def _parse_args(self):
        parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
        self._init_global_parser(parser)
        subparsers = parser.add_subparsers(title="command", dest="command")
        subparser = subparsers.add_parser("help", help="show help")
        for cmd_name, cmd in self.commands.items():
            subparser = subparsers.add_parser(
                cmd_name, help=cmd.desc
            )  # pylint: disable=protected-access
            for cmd_parser in cmd._parse_args:  # pylint: disable=protected-access
                cmd_parser(subparser)
        self.global_args = parser.parse_args()
        if self.global_args.version:
            self.global_args.command = "version"
        if not self.global_args.command or self.global_args.command == "help":
            parser.print_help()
            sys.exit(-1)
        return self.global_args

    @staticmethod
    def _init_global_parser(parser):
        parser.add_argument("-v", "--version", help="show version", action="store_true")
        parser.add_argument(
            "--in-pod",
            help="pod creation",
            metavar="in_pod",
            type=bool,
            default=False,
        )
        parser.add_argument(
            "--pod-args",
            help="custom arguments to be passed to `podman pod`",
            metavar="pod_args",
            type=str,
            default="--infra=false --share=",
        )
        parser.add_argument(
            "--env-file",
            help="Specify an alternate environment file",
            metavar="env_file",
            type=str,
            default=".env",
        )
        parser.add_argument(
            "-f",
            "--file",
            help="Specify an alternate compose file (default: docker-compose.yml)",
            metavar="file",
            action="append",
            default=[],
        )
        parser.add_argument(
            "-p",
            "--project-name",
            help="Specify an alternate project name (default: directory name)",
            type=str,
            default=None,
        )
        parser.add_argument(
            "--podman-path",
            help="Specify an alternate path to podman (default: use location in $PATH variable)",
            type=str,
            default="podman",
        )
        parser.add_argument(
            "--podman-args",
            help="custom global arguments to be passed to `podman`",
            metavar="args",
            action="append",
            default=[],
        )
        for podman_cmd in PODMAN_CMDS:
            parser.add_argument(
                f"--podman-{podman_cmd}-args",
                help=f"custom arguments to be passed to `podman {podman_cmd}`",
                metavar="args",
                action="append",
                default=[],
            )
        parser.add_argument(
            "--no-ansi",
            help="Do not print ANSI control characters",
            action="store_true",
        )
        parser.add_argument(
            "--no-cleanup",
            help="Do not stop and remove existing pod & containers",
            action="store_true",
        )
        parser.add_argument(
            "--dry-run",
            help="No action; perform a simulation of commands",
            action="store_true",
        )


podman_compose = PodmanCompose()

###################
# decorators to add commands and parse options
###################


class cmd_run:  # pylint: disable=invalid-name,too-few-public-methods
    def __init__(self, compose, cmd_name, cmd_desc=None):
        self.compose = compose
        self.cmd_name = cmd_name
        self.cmd_desc = cmd_desc

    def __call__(self, func):
        def wrapped(*args, **kw):
            return func(*args, **kw)

        wrapped._compose = self.compose
        # Trim extra indentation at start of multiline docstrings.
        wrapped.desc = self.cmd_desc or re.sub(r"^\s+", "", func.__doc__)
        wrapped._parse_args = []
        self.compose.commands[self.cmd_name] = wrapped
        return wrapped


class cmd_parse:  # pylint: disable=invalid-name,too-few-public-methods
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


@cmd_run(podman_compose, "version", "show version")
def compose_version(compose, args):
    if getattr(args, "short", False):
        print(__version__)
        return
    if getattr(args, "format", "pretty") == "json":
        res = {"version": __version__}
        print(json.dumps(res))
        return
    print("podman-compose version", __version__)
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


@cmd_run(podman_compose, "wait", "wait running containers to stop")
def compose_wait(compose, args):  # pylint: disable=unused-argument
    containers = [cnt["name"] for cnt in compose.containers]
    cmd_args = ["--"]
    cmd_args.extend(containers)
    compose.podman.exec([], "wait", cmd_args)


@cmd_run(podman_compose, "systemd")
def compose_systemd(compose, args):
    """
    create systemd unit file and register its compose stacks

    When first installed type `sudo podman-compose systemd -a create-unit`
    later you can add a compose stack by running `podman-compose systemd -a register`
    then you can start/stop your stack with `systemctl --user start podman-compose@<PROJ>`
    """
    stacks_dir = ".config/containers/compose/projects"
    if args.action == "register":
        proj_name = compose.project_name
        fn = os.path.expanduser(f"~/{stacks_dir}/{proj_name}.env")
        os.makedirs(os.path.dirname(fn), exist_ok=True)
        print(f"writing [{fn}]: ...")
        with open(fn, "w", encoding="utf-8") as f:
            for k, v in compose.environ.items():
                if k.startswith("COMPOSE_") or k.startswith("PODMAN_"):
                    f.write(f"{k}={v}\n")
        print(f"writing [{fn}]: done.")
        print("\n\ncreating the pod without starting it: ...\n\n")
        process = subprocess.run([script, "up", "--no-start"], check=False)
        print("\nfinal exit code is ", process.returncode)
        username = getpass.getuser()
        print(
            f"""
you can use systemd commands like enable, start, stop, status, cat
all without `sudo` like this:

\t\tsystemctl --user enable --now 'podman-compose@{proj_name}'
\t\tsystemctl --user status 'podman-compose@{proj_name}'
\t\tjournalctl --user -xeu 'podman-compose@{proj_name}'

and for that to work outside a session
you might need to run the following command *once*

\t\tsudo loginctl enable-linger '{username}'

you can use podman commands like:

\t\tpodman pod ps
\t\tpodman pod stats 'pod_{proj_name}'
\t\tpodman pod logs --tail=10 -f 'pod_{proj_name}'
"""
        )
    elif args.action in ("list", "ls"):
        ls = glob.glob(os.path.expanduser(f"~/{stacks_dir}/*.env"))
        for i in ls:
            print(os.path.basename(i[:-4]))
    elif args.action == "create-unit":
        fn = "/etc/systemd/user/podman-compose@.service"
        out = f"""\
# {fn}

[Unit]
Description=%i rootless pod (podman-compose)

[Service]
Type=simple
EnvironmentFile=%h/{stacks_dir}/%i.env
ExecStartPre=-{script} up --no-start
ExecStartPre=/usr/bin/podman pod start pod_%i
ExecStart={script} wait
ExecStop=/usr/bin/podman pod stop pod_%i

[Install]
WantedBy=default.target
"""
        if os.access(os.path.dirname(fn), os.W_OK):
            print(f"writing [{fn}]: ...")
            with open(fn, "w", encoding="utf-8") as f:
                f.write(out)
            print(f"writing [{fn}]: done.")
            print(
                """
while in your project type `podman-compose systemd -a register`
"""
            )
        else:
            print(out)
            log(f"Could not write to [{fn}], use 'sudo'")


@cmd_run(podman_compose, "pull", "pull stack images")
def compose_pull(compose, args):
    img_containers = [cnt for cnt in compose.containers if "image" in cnt]
    if args.services:
        services = set(args.services)
        img_containers = [cnt for cnt in img_containers if cnt["_service"] in services]
    images = {cnt["image"] for cnt in img_containers}
    if not args.force_local:
        local_images = {cnt["image"] for cnt in img_containers if is_local(cnt)}
        images -= local_images
    for image in images:
        compose.podman.run([], "pull", [image], sleep=0)


@cmd_run(podman_compose, "push", "push stack images")
def compose_push(compose, args):
    services = set(args.services)
    for cnt in compose.containers:
        if "build" not in cnt:
            continue
        if services and cnt["_service"] not in services:
            continue
        compose.podman.run([], "push", [cnt["image"]], sleep=0)


def build_one(compose, args, cnt):
    if "build" not in cnt:
        return
    if getattr(args, "if_not_exists", None):
        try:
            img_id = compose.podman.output(
                [], "inspect", ["-t", "image", "-f", "{{.Id}}", cnt["image"]]
            )
        except subprocess.CalledProcessError:
            img_id = None
        if img_id:
            return
    build_desc = cnt["build"]
    if not hasattr(build_desc, "items"):
        build_desc = {"context": build_desc}
    ctx = build_desc.get("context", ".")
    dockerfile = build_desc.get("dockerfile", None)
    if dockerfile:
        dockerfile = os.path.join(ctx, dockerfile)
    else:
        dockerfile_alts = [
            "Containerfile",
            "ContainerFile",
            "containerfile",
            "Dockerfile",
            "DockerFile",
            "dockerfile",
        ]
        for dockerfile in dockerfile_alts:
            dockerfile = os.path.join(ctx, dockerfile)
            if os.path.exists(dockerfile):
                break
    if not os.path.exists(dockerfile):
        raise OSError("Dockerfile not found in " + ctx)
    build_args = ["-f", dockerfile, "-t", cnt["image"]]
    for secret in build_desc.get("secrets", []):
        build_args.extend(get_secret_args(compose, cnt, secret))
    for tag in build_desc.get("tags", []):
        build_args.extend(["-t", tag])
    if "target" in build_desc:
        build_args.extend(["--target", build_desc["target"]])
    container_to_ulimit_args(cnt, build_args)
    if getattr(args, "no_cache", None):
        build_args.append("--no-cache")
    if getattr(args, "pull_always", None):
        build_args.append("--pull-always")
    elif getattr(args, "pull", None):
        build_args.append("--pull")
    args_list = norm_as_list(build_desc.get("args", {}))
    for build_arg in args_list + args.build_arg:
        build_args.extend(
            (
                "--build-arg",
                build_arg,
            )
        )
    build_args.append(ctx)
    compose.podman.run([], "build", build_args, sleep=0)


@cmd_run(podman_compose, "build", "build stack images")
def compose_build(compose, args):
    if args.services:
        container_names_by_service = compose.container_names_by_service
        compose.assert_services(args.services)
        for service in args.services:
            cnt = compose.container_by_name[container_names_by_service[service][0]]
            build_one(compose, args, cnt)
    else:
        for cnt in compose.containers:
            build_one(compose, args, cnt)


def create_pods(compose, args):  # pylint: disable=unused-argument
    for pod in compose.pods:
        podman_args = [
            "create",
            "--name=" + pod["name"],
        ]
        if args.pod_args:
            podman_args.extend(shlex.split(args.pod_args))
        # if compose.podman_version and not strverscmp_lt(compose.podman_version, "3.4.0"):
        #    podman_args.append("--infra-name={}_infra".format(pod["name"]))
        ports = pod.get("ports", None) or []
        if isinstance(ports, str):
            ports = [ports]
        for i in ports:
            podman_args.extend(["-p", str(i)])
        compose.podman.run([], "pod", podman_args)


def get_excluded(compose, args):
    excluded = set()
    if args.services:
        excluded = set(compose.services)
        for service in args.services:
            excluded -= compose.services[service]["_deps"]
            excluded.discard(service)
    log("** excluding: ", excluded)
    return excluded


@cmd_run(
    podman_compose, "up", "Create and start the entire stack or some of its services"
)
def compose_up(compose, args):
    proj_name = compose.project_name
    excluded = get_excluded(compose, args)
    if not args.no_build:
        # `podman build` does not cache, so don't always build
        build_args = argparse.Namespace(if_not_exists=(not args.build), **args.__dict__)
        compose.commands["build"](compose, build_args)

    hashes = (
        compose.podman.output(
            [],
            "ps",
            [
                "--filter",
                f"label=io.podman.compose.project={proj_name}",
                "-a",
                "--format",
                '{{ index .Labels "io.podman.compose.config-hash"}}',
            ],
        )
        .decode("utf-8")
        .splitlines()
    )
    diff_hashes = [i for i in hashes if i and i != compose.yaml_hash]
    if args.force_recreate or len(diff_hashes):
        log("recreating: ...")
        down_args = argparse.Namespace(**dict(args.__dict__, volumes=False))
        compose.commands["down"](compose, down_args)
        log("recreating: done\n\n")
    # args.no_recreate disables check for changes (which is not implemented)

    podman_command = "run" if args.detach and not args.no_start else "create"

    create_pods(compose, args)
    for cnt in compose.containers:
        if cnt["_service"] in excluded:
            log("** skipping: ", cnt["name"])
            continue
        podman_args = container_to_args(compose, cnt, detached=args.detach)
        subproc = compose.podman.run([], podman_command, podman_args)
        if podman_command == "run" and subproc and subproc.returncode:
            compose.podman.run([], "start", [cnt["name"]])
    if args.no_start or args.detach or args.dry_run:
        return
    # TODO: handle already existing
    # TODO: if error creating do not enter loop
    # TODO: colors if sys.stdout.isatty()
    exit_code_from = args.__dict__.get("exit_code_from", None)
    if exit_code_from:
        args.abort_on_container_exit = True

    threads = []

    max_service_length = 0
    for cnt in compose.containers:
        curr_length = len(cnt["_service"])
        max_service_length = (
            curr_length if curr_length > max_service_length else max_service_length
        )
    has_sed = os.path.isfile("/bin/sed")
    for i, cnt in enumerate(compose.containers):
        # Add colored service prefix to output by piping output through sed
        color_idx = i % len(compose.console_colors)
        color = compose.console_colors[color_idx]
        space_suffix = " " * (max_service_length - len(cnt["_service"]) + 1)
        log_formatter = "s/^/{}[{}]{}|\x1B[0m\\ /;".format(
            color, cnt["_service"], space_suffix
        )
        log_formatter = ["sed", "-e", log_formatter] if has_sed else None
        if cnt["_service"] in excluded:
            log("** skipping: ", cnt["name"])
            continue
        # TODO: remove sleep from podman.run
        obj = compose if exit_code_from == cnt["_service"] else None
        thread = Thread(
            target=compose.podman.run,
            args=[[], "start", ["-a", cnt["name"]]],
            kwargs={"obj": obj, "log_formatter": log_formatter},
            daemon=True,
            name=cnt["name"],
        )
        thread.start()
        threads.append(thread)
        time.sleep(1)

    while threads:
        to_remove = []
        for thread in threads:
            thread.join(timeout=1.0)
            if not thread.is_alive():
                to_remove.append(thread)
                if args.abort_on_container_exit:
                    time.sleep(1)
                    exit_code = (
                        compose.exit_code if compose.exit_code is not None else -1
                    )
                    sys.exit(exit_code)
        for thread in to_remove:
            threads.remove(thread)


def get_volume_names(compose, cnt):
    proj_name = compose.project_name
    basedir = compose.dirname
    srv_name = cnt["_service"]
    ls = []
    for volume in cnt.get("volumes", []):
        if is_str(volume):
            volume = parse_short_mount(volume, basedir)
        volume = fix_mount_dict(compose, volume, proj_name, srv_name)
        mount_type = volume["type"]
        if mount_type != "volume":
            continue
        volume_name = (volume.get("_vol", None) or {}).get("name", None)
        ls.append(volume_name)
    return ls


@cmd_run(podman_compose, "down", "tear down entire stack")
def compose_down(compose, args):
    excluded = get_excluded(compose, args)
    podman_args = []
    timeout_global = getattr(args, "timeout", None)
    containers = list(reversed(compose.containers))

    for cnt in containers:
        if cnt["_service"] in excluded:
            continue
        podman_stop_args = [*podman_args]
        timeout = timeout_global
        if timeout is None:
            timeout_str = cnt.get("stop_grace_period", None) or STOP_GRACE_PERIOD
            timeout = str_to_seconds(timeout_str)
        if timeout is not None:
            podman_stop_args.extend(["-t", str(timeout)])
        compose.podman.run([], "stop", [*podman_stop_args, cnt["name"]], sleep=0)
    for cnt in containers:
        if cnt["_service"] in excluded:
            continue
        compose.podman.run([], "rm", [cnt["name"]], sleep=0)
    if args.remove_orphans:
        names = (
            compose.podman.output(
                [],
                "ps",
                [
                    "--filter",
                    f"label=io.podman.compose.project={compose.project_name}",
                    "-a",
                    "--format",
                    "{{ .Names }}",
                ],
            )
            .decode("utf-8")
            .splitlines()
        )
        for name in names:
            compose.podman.run([], "stop", [*podman_args, name], sleep=0)
        for name in names:
            compose.podman.run([], "rm", [name], sleep=0)
    if args.volumes:
        vol_names_to_keep = set()
        for cnt in containers:
            if cnt["_service"] not in excluded:
                continue
            vol_names_to_keep.update(get_volume_names(compose, cnt))
        log("keep", vol_names_to_keep)
        for volume_name in compose.podman.volume_ls():
            if volume_name in vol_names_to_keep:
                continue
            compose.podman.run([], "volume", ["rm", volume_name])

    if excluded:
        return
    for pod in compose.pods:
        compose.podman.run([], "pod", ["rm", pod["name"]], sleep=0)


@cmd_run(podman_compose, "ps", "show status of containers")
def compose_ps(compose, args):
    proj_name = compose.project_name
    if args.quiet is True:
        compose.podman.run(
            [],
            "ps",
            [
                "-a",
                "--format",
                "{{.ID}}",
                "--filter",
                f"label=io.podman.compose.project={proj_name}",
            ],
        )
    else:
        compose.podman.run(
            [], "ps", ["-a", "--filter", f"label=io.podman.compose.project={proj_name}"]
        )


@cmd_run(
    podman_compose,
    "run",
    "create a container similar to a service to run a one-off command",
)
def compose_run(compose, args):
    create_pods(compose, args)
    compose.assert_services(args.service)
    container_names = compose.container_names_by_service[args.service]
    container_name = container_names[0]
    cnt = dict(compose.container_by_name[container_name])
    deps = cnt["_deps"]
    if deps and not args.no_deps:
        up_args = argparse.Namespace(
            **dict(
                args.__dict__,
                detach=True,
                services=deps,
                # defaults
                no_build=False,
                build=None,
                force_recreate=False,
                no_start=False,
                no_cache=False,
                build_arg=[],
            )
        )
        compose.commands["up"](compose, up_args)
    # adjust one-off container options
    name0 = "{}_{}_tmp{}".format(
        compose.project_name, args.service, random.randrange(0, 65536)
    )
    cnt["name"] = args.name or name0
    if args.entrypoint:
        cnt["entrypoint"] = args.entrypoint
    if args.user:
        cnt["user"] = args.user
    if args.workdir:
        cnt["working_dir"] = args.workdir
    env = dict(cnt.get("environment", {}))
    if args.env:
        additional_env_vars = dict(map(lambda each: each.split("="), args.env))
        env.update(additional_env_vars)
        cnt["environment"] = env
    if not args.service_ports:
        for k in ("expose", "publishall", "ports"):
            try:
                del cnt[k]
            except KeyError:
                pass
    if args.volume:
        # TODO: handle volumes
        volumes = clone(cnt.get("volumes", None) or [])
        volumes.extend(args.volume)
        cnt["volumes"] = volumes
    cnt["tty"] = not args.T
    if args.cnt_command is not None and len(args.cnt_command) > 0:
        cnt["command"] = args.cnt_command
    # can't restart and --rm
    if args.rm and "restart" in cnt:
        del cnt["restart"]
    # run podman
    podman_args = container_to_args(compose, cnt, args.detach)
    if not args.detach:
        podman_args.insert(1, "-i")
        if args.rm:
            podman_args.insert(1, "--rm")
    p = compose.podman.run([], "run", podman_args, sleep=0)
    sys.exit(p.returncode)


@cmd_run(podman_compose, "exec", "execute a command in a running container")
def compose_exec(compose, args):
    compose.assert_services(args.service)
    container_names = compose.container_names_by_service[args.service]
    container_name = container_names[args.index - 1]
    cnt = compose.container_by_name[container_name]
    podman_args = ["--interactive"]
    if args.privileged:
        podman_args += ["--privileged"]
    if args.user:
        podman_args += ["--user", args.user]
    if args.workdir:
        podman_args += ["--workdir", args.workdir]
    if not args.T:
        podman_args += ["--tty"]
    env = dict(cnt.get("environment", {}))
    if args.env:
        additional_env_vars = dict(
            map(lambda each: each.split("=") if "=" in each else (each, None), args.env)
        )
        env.update(additional_env_vars)
    for name, value in env.items():
        podman_args += ["--env", f"{name}" if value is None else f"{name}={value}"]
    podman_args += [container_name]
    if args.cnt_command is not None and len(args.cnt_command) > 0:
        podman_args += args.cnt_command
    p = compose.podman.run([], "exec", podman_args, sleep=0)
    sys.exit(p.returncode)


def transfer_service_status(compose, args, action):
    # TODO: handle dependencies, handle creations
    container_names_by_service = compose.container_names_by_service
    if not args.services:
        args.services = container_names_by_service.keys()
    compose.assert_services(args.services)
    targets = []
    for service in args.services:
        if service not in container_names_by_service:
            raise ValueError("unknown service: " + service)
        targets.extend(container_names_by_service[service])
    if action in ["stop", "restart"]:
        targets = list(reversed(targets))
    podman_args = []
    timeout_global = getattr(args, "timeout", None)
    for target in targets:
        if action != "start":
            timeout = timeout_global
            if timeout is None:
                timeout_str = (
                    compose.container_by_name[target].get("stop_grace_period", None)
                    or STOP_GRACE_PERIOD
                )
                timeout = str_to_seconds(timeout_str)
            if timeout is not None:
                podman_args.extend(["-t", str(timeout)])
        compose.podman.run([], action, podman_args + [target], sleep=0)


@cmd_run(podman_compose, "start", "start specific services")
def compose_start(compose, args):
    transfer_service_status(compose, args, "start")


@cmd_run(podman_compose, "stop", "stop specific services")
def compose_stop(compose, args):
    transfer_service_status(compose, args, "stop")


@cmd_run(podman_compose, "restart", "restart specific services")
def compose_restart(compose, args):
    transfer_service_status(compose, args, "restart")


@cmd_run(podman_compose, "logs", "show logs from services")
def compose_logs(compose, args):
    container_names_by_service = compose.container_names_by_service
    if not args.services and not args.latest:
        args.services = container_names_by_service.keys()
    compose.assert_services(args.services)
    targets = []
    for service in args.services:
        targets.extend(container_names_by_service[service])
    podman_args = []
    if args.follow:
        podman_args.append("-f")
    if args.latest:
        podman_args.append("-l")
    if args.names:
        podman_args.append("-n")
    if args.since:
        podman_args.extend(["--since", args.since])
    # the default value is to print all logs which is in podman = 0 and not
    # needed to be passed
    if args.tail and args.tail != "all":
        podman_args.extend(["--tail", args.tail])
    if args.timestamps:
        podman_args.append("-t")
    if args.until:
        podman_args.extend(["--until", args.until])
    for target in targets:
        podman_args.append(target)
    compose.podman.run([], "logs", podman_args)


@cmd_run(podman_compose, "config", "displays the compose file")
def compose_config(compose, args):
    if args.services:
        for service in compose.services:
            print(service)
        return
    print(compose.merged_yaml)


@cmd_run(podman_compose, "port", "Prints the public port for a port binding.")
def compose_port(compose, args):
    # TODO - deal with pod index
    compose.assert_services(args.service)
    containers = compose.container_names_by_service[args.service]
    container_ports = list(
        itertools.chain(*(compose.container_by_name[c]["ports"] for c in containers))
    )

    def _published_target(port_string):
        published, target = port_string.split(":")[-2:]
        return int(published), int(target)

    select_udp = args.protocol == "udp"
    published, target = None, None
    for p in container_ports:
        is_udp = p[-4:] == "/udp"

        if select_udp and is_udp:
            published, target = _published_target(p[-4:])
        if not select_udp and not is_udp:
            published, target = _published_target(p)

        if target == args.private_port:
            print(published)
            return


@cmd_run(podman_compose, "pause", "Pause all running containers")
def compose_pause(compose, args):
    container_names_by_service = compose.container_names_by_service
    if not args.services:
        args.services = container_names_by_service.keys()
    targets = []
    for service in args.services:
        targets.extend(container_names_by_service[service])
    compose.podman.run([], "pause", targets)


@cmd_run(podman_compose, "unpause", "Unpause all running containers")
def compose_unpause(compose, args):
    container_names_by_service = compose.container_names_by_service
    if not args.services:
        args.services = container_names_by_service.keys()
    targets = []
    for service in args.services:
        targets.extend(container_names_by_service[service])
    compose.podman.run([], "unpause", targets)


@cmd_run(
    podman_compose, "kill", "Kill one or more running containers with a specific signal"
)
def compose_kill(compose, args):
    # to ensure that the user did not execute the command by mistake
    if not args.services and not args.all:
        print(
            "Error: you must provide at least one service name or use (--all) to kill all services"
        )
        sys.exit()

    container_names_by_service = compose.container_names_by_service
    podman_args = []

    if args.signal:
        podman_args.extend(["--signal", args.signal])

    if args.all is True:
        services = container_names_by_service.keys()
        targets = []
        for service in services:
            targets.extend(container_names_by_service[service])
        for target in targets:
            podman_args.append(target)
        compose.podman.run([], "kill", podman_args)

    if args.services:
        targets = []
        for service in args.services:
            targets.extend(container_names_by_service[service])
        for target in targets:
            podman_args.append(target)
        compose.podman.run([], "kill", podman_args)


###################
# command arguments parsing
###################


@cmd_parse(podman_compose, "version")
def compose_version_parse(parser):
    parser.add_argument(
        "-f",
        "--format",
        choices=["pretty", "json"],
        default="pretty",
        help="Format the output",
    )
    parser.add_argument(
        "--short",
        action="store_true",
        help="Shows only Podman Compose's version number",
    )


@cmd_parse(podman_compose, "up")
def compose_up_parse(parser):
    parser.add_argument(
        "-d",
        "--detach",
        action="store_true",
        help="Detached mode: Run container in the background, print new container name. Incompatible with --abort-on-container-exit.",
    )
    parser.add_argument(
        "--no-color", action="store_true", help="Produce monochrome output."
    )
    parser.add_argument(
        "--quiet-pull",
        action="store_true",
        help="Pull without printing progress information.",
    )
    parser.add_argument(
        "--no-deps", action="store_true", help="Don't start linked services."
    )
    parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="Recreate containers even if their configuration and image haven't changed.",
    )
    parser.add_argument(
        "--always-recreate-deps",
        action="store_true",
        help="Recreate dependent containers. Incompatible with --no-recreate.",
    )
    parser.add_argument(
        "--no-recreate",
        action="store_true",
        help="If containers already exist, don't recreate them. Incompatible with --force-recreate and -V.",
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="Don't build an image, even if it's missing.",
    )
    parser.add_argument(
        "--no-start",
        action="store_true",
        help="Don't start the services after creating them.",
    )
    parser.add_argument(
        "--build", action="store_true", help="Build images before starting containers."
    )
    parser.add_argument(
        "--abort-on-container-exit",
        action="store_true",
        help="Stops all containers if any container was stopped. Incompatible with -d.",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=None,
        help="Use this timeout in seconds for container shutdown when attached or when containers are already running. (default: 10)",
    )
    parser.add_argument(
        "-V",
        "--renew-anon-volumes",
        action="store_true",
        help="Recreate anonymous volumes instead of retrieving data from the previous containers.",
    )
    parser.add_argument(
        "--remove-orphans",
        action="store_true",
        help="Remove containers for services not defined in the Compose file.",
    )
    parser.add_argument(
        "--scale",
        metavar="SERVICE=NUM",
        action="append",
        help="Scale SERVICE to NUM instances. Overrides the `scale` setting in the Compose file if present.",
    )
    parser.add_argument(
        "--exit-code-from",
        metavar="SERVICE",
        type=str,
        default=None,
        help="Return the exit code of the selected service container. Implies --abort-on-container-exit.",
    )


@cmd_parse(podman_compose, "down")
def compose_down_parse(parser):
    parser.add_argument(
        "-v",
        "--volumes",
        action="store_true",
        default=False,
        help="Remove named volumes declared in the `volumes` section of the Compose file and "
        "anonymous volumes attached to containers.",
    )
    parser.add_argument(
        "--remove-orphans",
        action="store_true",
        help="Remove containers for services not defined in the Compose file.",
    )


@cmd_parse(podman_compose, "run")
def compose_run_parse(parser):
    parser.add_argument(
        "-d",
        "--detach",
        action="store_true",
        help="Detached mode: Run container in the background, print new container name.",
    )
    parser.add_argument(
        "--name", type=str, default=None, help="Assign a name to the container"
    )
    parser.add_argument(
        "--entrypoint",
        type=str,
        default=None,
        help="Override the entrypoint of the image.",
    )
    parser.add_argument(
        "-e",
        "--env",
        metavar="KEY=VAL",
        action="append",
        help="Set an environment variable (can be used multiple times)",
    )
    parser.add_argument(
        "-l",
        "--label",
        metavar="KEY=VAL",
        action="append",
        help="Add or override a label (can be used multiple times)",
    )
    parser.add_argument(
        "-u", "--user", type=str, default=None, help="Run as specified username or uid"
    )
    parser.add_argument(
        "--no-deps", action="store_true", help="Don't start linked services"
    )
    parser.add_argument(
        "--rm",
        action="store_true",
        help="Remove container after run. Ignored in detached mode.",
    )
    parser.add_argument(
        "-p",
        "--publish",
        action="append",
        help="Publish a container's port(s) to the host (can be used multiple times)",
    )
    parser.add_argument(
        "--service-ports",
        action="store_true",
        help="Run command with the service's ports enabled and mapped to the host.",
    )
    parser.add_argument(
        "-v",
        "--volume",
        action="append",
        help="Bind mount a volume (can be used multiple times)",
    )
    parser.add_argument(
        "-T",
        action="store_true",
        help="Disable pseudo-tty allocation. By default `podman-compose run` allocates a TTY.",
    )
    parser.add_argument(
        "-w",
        "--workdir",
        type=str,
        default=None,
        help="Working directory inside the container",
    )
    parser.add_argument("service", metavar="service", nargs=None, help="service name")
    parser.add_argument(
        "cnt_command",
        metavar="command",
        nargs=argparse.REMAINDER,
        help="command and its arguments",
    )


@cmd_parse(podman_compose, "exec")
def compose_exec_parse(parser):
    parser.add_argument(
        "-d",
        "--detach",
        action="store_true",
        help="Detached mode: Run container in the background, print new container name.",
    )
    parser.add_argument(
        "--privileged",
        action="store_true",
        default=False,
        help="Give the process extended Linux capabilities inside the container",
    )
    parser.add_argument(
        "-u", "--user", type=str, default=None, help="Run as specified username or uid"
    )
    parser.add_argument(
        "-T",
        action="store_true",
        help="Disable pseudo-tty allocation. By default `podman-compose run` allocates a TTY.",
    )
    parser.add_argument(
        "--index",
        type=int,
        default=1,
        help="Index of the container if there are multiple instances of a service",
    )
    parser.add_argument(
        "-e",
        "--env",
        metavar="KEY=VAL",
        action="append",
        help="Set an environment variable (can be used multiple times)",
    )
    parser.add_argument(
        "-w",
        "--workdir",
        type=str,
        default=None,
        help="Working directory inside the container",
    )
    parser.add_argument("service", metavar="service", nargs=None, help="service name")
    parser.add_argument(
        "cnt_command",
        metavar="command",
        nargs=argparse.REMAINDER,
        help="command and its arguments",
    )


@cmd_parse(podman_compose, ["down", "stop", "restart"])
def compose_parse_timeout(parser):
    parser.add_argument(
        "-t",
        "--timeout",
        help="Specify a shutdown timeout in seconds. ",
        type=int,
        default=None,
    )


@cmd_parse(podman_compose, ["logs"])
def compose_logs_parse(parser):
    parser.add_argument(
        "-f",
        "--follow",
        action="store_true",
        help="Follow log output. The default is false",
    )
    parser.add_argument(
        "-l",
        "--latest",
        action="store_true",
        help="Act on the latest container podman is aware of",
    )
    parser.add_argument(
        "-n",
        "--names",
        action="store_true",
        help="Output the container name in the log",
    )
    parser.add_argument(
        "--since", help="Show logs since TIMESTAMP", type=str, default=None
    )
    parser.add_argument(
        "-t", "--timestamps", action="store_true", help="Show timestamps."
    )
    parser.add_argument(
        "--tail",
        help="Number of lines to show from the end of the logs for each " "container.",
        type=str,
        default="all",
    )
    parser.add_argument(
        "--until", help="Show logs until TIMESTAMP", type=str, default=None
    )
    parser.add_argument(
        "services", metavar="services", nargs="*", default=None, help="service names"
    )


@cmd_parse(podman_compose, "systemd")
def compose_systemd_parse(parser):
    parser.add_argument(
        "-a",
        "--action",
        choices=["register", "create-unit", "list", "ls"],
        default="register",
        help="create systemd unit file or register compose stack to it",
    )


@cmd_parse(podman_compose, "pull")
def compose_pull_parse(parser):
    parser.add_argument(
        "--force-local",
        action="store_true",
        default=False,
        help="Also pull unprefixed images for services which have a build section",
    )
    parser.add_argument(
        "services", metavar="services", nargs="*", help="services to pull"
    )


@cmd_parse(podman_compose, "push")
def compose_push_parse(parser):
    parser.add_argument(
        "--ignore-push-failures",
        action="store_true",
        help="Push what it can and ignores images with push failures. (not implemented)",
    )
    parser.add_argument(
        "services", metavar="services", nargs="*", help="services to push"
    )


@cmd_parse(podman_compose, "ps")
def compose_ps_parse(parser):
    parser.add_argument(
        "-q", "--quiet", help="Only display container IDs", action="store_true"
    )


@cmd_parse(podman_compose, ["build", "up"])
def compose_build_up_parse(parser):
    parser.add_argument(
        "--pull",
        help="attempt to pull a newer version of the image",
        action="store_true",
    )
    parser.add_argument(
        "--pull-always",
        help="attempt to pull a newer version of the image, Raise an error even if the image is present locally.",
        action="store_true",
    )
    parser.add_argument(
        "--build-arg",
        metavar="key=val",
        action="append",
        default=[],
        help="Set build-time variables for services.",
    )
    parser.add_argument(
        "--no-cache",
        help="Do not use cache when building the image.",
        action="store_true",
    )


@cmd_parse(podman_compose, ["build", "up", "down", "start", "stop", "restart"])
def compose_build_parse(parser):
    parser.add_argument(
        "services",
        metavar="services",
        nargs="*",
        default=None,
        help="affected services",
    )


@cmd_parse(podman_compose, "config")
def compose_config_parse(parser):
    parser.add_argument(
        "--services", help="Print the service names, one per line.", action="store_true"
    )


@cmd_parse(podman_compose, "port")
def compose_port_parse(parser):
    parser.add_argument(
        "--index",
        type=int,
        default=1,
        help="index of the container if there are multiple instances of a service",
    )
    parser.add_argument(
        "--protocol",
        choices=["tcp", "udp"],
        default="tcp",
        help="tcp or udp",
    )
    parser.add_argument("service", metavar="service", nargs=None, help="service name")
    parser.add_argument(
        "private_port",
        metavar="private_port",
        nargs=None,
        type=int,
        help="private port",
    )


@cmd_parse(podman_compose, ["pause", "unpause"])
def compose_pause_unpause_parse(parser):
    parser.add_argument(
        "services", metavar="services", nargs="*", default=None, help="service names"
    )


@cmd_parse(podman_compose, ["kill"])
def compose_kill_parse(parser):
    parser.add_argument(
        "services", metavar="services", nargs="*", default=None, help="service names"
    )
    parser.add_argument(
        "-s",
        "--signal",
        type=str,
        help="Signal to send to the container (default 'KILL')",
    )
    parser.add_argument(
        "-a",
        "--all",
        help="Signal all running containers",
        action="store_true",
    )


def main():
    podman_compose.run()


if __name__ == "__main__":
    main()
