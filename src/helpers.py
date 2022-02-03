#! /usr/bin/python3
# -*- coding: utf-8 -*-

# https://docs.docker.com/compose/compose-file/#service-configuration-reference
# https://docs.docker.com/samples/
# https://docs.docker.com/compose/gettingstarted/
# https://docs.docker.com/compose/django/
# https://docs.docker.com/compose/wordpress/

import sys
import os
import subprocess
import re
import hashlib
import json


import shlex

try:
    from shlex import quote as cmd_quote
except ImportError:
    from pipes import quote as cmd_quote

# import fnmatch
# fnmatch.fnmatchcase(env, "*_HOST")



# helper functions
is_str  = lambda s: isinstance(s, str)
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
    line = (sep.join(["{}".format(msg) for msg in msgs]))+end
    sys.stderr.write(line)
    sys.stderr.flush()

dir_re = re.compile("^[~/\.]")
propagation_re = re.compile("^(?:z|Z|O|U|r?shared|r?slave|r?private|r?unbindable|r?bind|(?:no)?(?:exec|dev|suid))$")
norm_re =  re.compile('[^-_a-z0-9]')
num_split_re = re.compile(r'(\d+|\D+)')


def ver_as_list(a):
    return [try_int(i, i) for i in num_split_re.findall(a)]

def strverscmp_lt(a, b):
    a_ls = ver_as_list(a or '')
    b_ls = ver_as_list(b or '')
    return a_ls < b_ls

def parse_short_mount(mount_str, basedir):
    mount_a = mount_str.split(':')
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
        if not mount_dst.startswith('/'):
            mount_dst, mount_opt = mount_a
            mount_src = None
    elif len(mount_a) == 3:
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
        mount_src = os.path.realpath(os.path.join(basedir, os.path.expanduser(mount_src)))
    else:
        # Named volume
        # - datavolume:/var/lib/mysql
        mount_type = "volume"
    mount_opts = filteri((mount_opt or '').split(','))
    for opt in mount_opts:
        if opt == 'ro': mount_opt_dict["read_only"] = True
        elif opt == 'rw': mount_opt_dict["read_only"] = False
        elif opt in ('consistent', 'delegated', 'cached'):
            mount_opt_dict["consistency"] = opt
        elif propagation_re.match(opt): mount_opt_dict["bind"] = dict(propagation=opt)
        else:
            # TODO: ignore
            raise ValueError("unknown mount option "+opt)
    return dict(type=mount_type, source=mount_src, target=mount_dst, **mount_opt_dict)

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
    if "_vol" in mount_dict: return mount_dict
    if mount_dict["type"] == "volume":
        vols = compose.vols
        source = mount_dict.get("source", None)
        vol = (vols.get(source, None) or {}) if source else {}
        name = vol.get('name', None) 
        mount_dict["_vol"] = vol
        # handle anonymouse or implied volume
        if not source:
            # missing source
            vol["name"] = "_".join([
                proj_name, srv_name,
                hashlib.sha256(mount_dict["target"].encode("utf-8")).hexdigest(),
            ])
        elif not name:
            external = vol.get("external", None)
            ext_name = external.get("name", None) if isinstance(external, dict) else None
            vol["name"] =  ext_name if ext_name else f"{proj_name}_{source}"
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

var_re = re.compile(r"""
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
""", re.VERBOSE)

def rec_subs(value, subs_dict):
    """
    do bash-like substitution in value and if list of dictionary do that recursively
    """
    if is_dict(value):
        value = dict([(k, rec_subs(v, subs_dict)) for k, v in value.items()])
    elif is_str(value):
        def convert(m):
            if m.group("escaped") is not None:
                return "$"
            name = m.group("named") or m.group("braced")
            value = subs_dict.get(name)
            if value == "" and m.group('empty'):
                value = None
            if value is not None:
                return "%s" % value
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
        dst = [("{}={}".format(k, v) if v is not None else k) for k, v in src.items()]
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
        soft = inner_value.get("soft", inner_value.get("hard", None))
        hard = inner_value.get("hard", inner_value.get("soft", None))
        return "{}:{}".format(soft, hard)
    elif is_list(inner_value): return norm_ulimit(norm_as_dict(inner_value))
    # if int or string return as is
    return inner_value

#def tr_identity(project_name, given_containers):
#    pod_name = f'pod_{project_name}'
#    pod = dict(name=pod_name)
#    containers = []
#    for cnt in given_containers:
#        containers.append(dict(cnt, pod=pod_name))
#    return [pod], containers

def tr_identity(project_name, given_containers):
    containers = []
    for cnt in given_containers:
        containers.append(dict(cnt))
    return [], containers


def assert_volume(compose, mount_dict):
    """
    inspect volume to get directory
    create volume if needed
    """
    vol = mount_dict.get("_vol", None)
    if mount_dict["type"] == "bind":
        basedir = os.path.realpath(compose.dirname)
        mount_src = mount_dict["source"]
        mount_src = os.path.realpath(os.path.join(basedir, os.path.expanduser(mount_src)))
        if not os.path.exists(mount_src):
            try:
                os.makedirs(mount_src, exist_ok=True)
            except OSError:
                pass
        return
    if mount_dict["type"] != "volume" or not vol or vol.get("external", None) or not vol.get("name", None): return
    proj_name = compose.project_name
    vol_name = vol["name"]
    log("podman volume inspect {vol_name} || podman volume create {vol_name}".format(vol_name=vol_name))
    # TODO: might move to using "volume list"
    # podman volume list --format '{{.Name}}\t{{.MountPoint}}' -f 'label=io.podman.compose.project=HERE'
    try: out = compose.podman.output([], "volume", ["inspect", vol_name]).decode('utf-8')
    except subprocess.CalledProcessError:
        labels = vol.get("labels", None) or []
        args = [
            "create",
            "--label", "io.podman.compose.project={}".format(proj_name),
            "--label", "com.docker.compose.project={}".format(proj_name),
        ]
        for item in norm_as_list(labels):
            args.extend(["--label", item])
        driver = vol.get("driver", None)
        if driver:
            args.extend(["--driver", driver])
        driver_opts = vol.get("driver_opts", None) or {}
        for opt, value in driver_opts.items():
            args.extend(["--opt", "{opt}={value}".format(opt=opt, value=value)])
        args.append(vol_name)
        compose.podman.output([], "volume", args)
        out = compose.podman.output([], "volume", ["inspect", vol_name]).decode('utf-8')

def mount_desc_to_mount_args(compose, mount_desc, srv_name, cnt_name):
    mount_type = mount_desc.get("type", None)
    vol = mount_desc.get("_vol", None) if mount_type=="volume" else None
    source = vol["name"] if vol else mount_desc.get("source", None)
    target = mount_desc["target"]
    opts = []
    if mount_desc.get(mount_type, None):
        # TODO: we might need to add mount_dict[mount_type]["propagation"] = "z"
        mount_prop = mount_desc.get(mount_type, {}).get("propagation", None)
        if mount_prop: opts.append("{}-propagation={}".format(mount_type, mount_prop))
    if mount_desc.get("read_only", False): opts.append("ro")
    if mount_type == 'tmpfs':
        tmpfs_opts = mount_desc.get("tmpfs", {})
        tmpfs_size = tmpfs_opts.get("size", None)
        if tmpfs_size:
            opts.append("tmpfs-size={}".format(tmpfs_size))
        tmpfs_mode = tmpfs_opts.get("mode", None)
        if tmpfs_mode:
            opts.append("tmpfs-mode={}".format(tmpfs_mode))
    opts = ",".join(opts)
    if mount_type == 'bind':
        return "type=bind,source={source},destination={target},{opts}".format(
            source=source,
            target=target,
            opts=opts
        ).rstrip(",")
    elif mount_type == 'volume':
        return "type=volume,source={source},destination={target},{opts}".format(
            source=source,
            target=target,
            opts=opts
        ).rstrip(",")
    elif mount_type == 'tmpfs':
        return "type=tmpfs,destination={target},{opts}".format(
            target=target,
            opts=opts
        ).rstrip(",")
    else:
        raise ValueError("unknown mount type:"+mount_type)

def container_to_ulimit_args(cnt, podman_args):
    ulimit = cnt.get('ulimits', [])
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

def mount_desc_to_volume_args(compose, mount_desc, srv_name, cnt_name):
    mount_type = mount_desc["type"]
    if mount_type != 'bind' and mount_type != 'volume':
        raise ValueError("unknown mount type:"+mount_type)
    vol = mount_desc.get("_vol", None) if mount_type=="volume" else None
    source = vol["name"] if vol else mount_desc.get("source", None)
    if not source:
        raise ValueError(f"missing mount source for {mount_type} on {srv_name}")
    target = mount_desc["target"]
    opts = []

    propagations = set(filteri(mount_desc.get(mount_type, {}).get("propagation", "").split(',')))
    if mount_type != 'bind':
        propagations.update(filteri(mount_desc.get('bind', {}).get("propagation", "").split(',')))
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
        opts.append('ro' if read_only else 'rw')
    args = f'{source}:{target}'
    if opts: args += ':' + ','.join(opts)
    return args

def get_mnt_dict(compose, cnt, volume):
    proj_name = compose.project_name
    srv_name = cnt['_service']
    basedir = compose.dirname
    if is_str(volume):
        volume = parse_short_mount(volume, basedir)
    return fix_mount_dict(compose, volume, proj_name, srv_name)

def get_mount_args(compose, cnt, volume):
    volume = get_mnt_dict(compose, cnt, volume)
    proj_name = compose.project_name
    srv_name = cnt['_service']
    mount_type = volume["type"]
    assert_volume(compose, volume)
    if compose._prefer_volume_over_mount:
        if mount_type == 'tmpfs':
            # TODO: --tmpfs /tmp:rw,size=787448k,mode=1777
            args = volume['target']
            tmpfs_opts = volume.get("tmpfs", {})
            opts = []
            size = tmpfs_opts.get("size", None)
            if size: opts.append('size={}'.format(size))
            mode = tmpfs_opts.get("mode", None)
            if mode: opts.append('mode={}'.format(mode))
            if opts: args += ':' + ','.join(opts)
            return ['--tmpfs', args]
        else:
            args = mount_desc_to_volume_args(compose, volume, srv_name, cnt['name'])
            return ['-v', args]
    else:
        args = mount_desc_to_mount_args(compose, volume, srv_name, cnt['name'])
        return ['--mount', args]


def get_secret_args(compose, cnt, secret):
    secret_name = secret if is_str(secret) else secret.get('source', None)
    if not secret_name or secret_name not in compose.declared_secrets.keys():
        raise ValueError(
            'ERROR: undeclared secret: "{}", service: "{}"'
            .format(secret, cnt['_service'])
        )
    declared_secret = compose.declared_secrets[secret_name]

    source_file = declared_secret.get('file', None)
    dest_file = ''
    secret_opts = ''

    target = None if is_str(secret) else secret.get('target', None)
    uid = None if is_str(secret) else secret.get('uid', None)
    gid = None if is_str(secret) else secret.get('gid', None)
    mode = None if is_str(secret) else secret.get('mode', None)

    if source_file:
        if not target:
            dest_file = '/run/secrets/{}'.format(secret_name)
        elif not target.startswith("/"):
            dest_file = '/run/secrets/{}'.format(target if target else secret_name)
        else:
            dest_file = target
        volume_ref = [
            '--volume', '{}:{}:ro,rprivate,rbind'.format(source_file, dest_file)
        ]
        if uid or gid or mode:
            log(
                'WARNING: Service "{}" uses secret "{}" with uid, gid, or mode.'
                    .format(cnt['_service'], target if target else secret_name)
                + ' These fields are not supported by this implementation of the Compose file'
            )
        return volume_ref
    # v3.5 and up added external flag, earlier the spec
    # only required a name to be specified.
    # docker-compose does not support external secrets outside of swarm mode.
    # However accessing these via podman is trivial
    # since these commands are directly translated to
    # podman-create commands, albiet we can only support a 1:1 mapping
    # at the moment
    if declared_secret.get('external', False) or declared_secret.get('name', None):
        secret_opts += ',uid={}'.format(uid) if uid else ''
        secret_opts += ',gid={}'.format(gid) if gid else ''
        secret_opts += ',mode={}'.format(mode) if mode else ''
        # The target option is only valid for type=env,
        # which in an ideal world would work
        # for type=mount as well.
        # having a custom name for the external secret
        # has the same problem as well
        ext_name = declared_secret.get('name', None)
        err_str = 'ERROR: Custom name/target reference "{}" for mounted external secret "{}" is not supported'
        if ext_name and ext_name != secret_name:
            raise ValueError(err_str.format(secret_name, ext_name))
        elif target and target != secret_name:
            raise ValueError(err_str.format(target, secret_name))
        elif target:
            log('WARNING: Service "{}" uses target: "{}" for secret: "{}".'
                    .format(cnt['_service'], target, secret_name)
                  + ' That is un-supported and a no-op and is ignored.')
        return [ '--secret', '{}{}'.format(secret_name, secret_opts) ]

    raise ValueError('ERROR: unparseable secret: "{}", service: "{}"'
                        .format(secret_name, cnt['_service']))


def container_to_res_args(cnt, podman_args):
    # v2 < https://docs.docker.com/compose/compose-file/compose-file-v2/#cpu-and-other-resources
    cpus_limit_v2 = try_float(cnt.get('cpus', None), None)
    cpu_shares_v2 = try_int(cnt.get('cpu_shares', None), None)
    mem_limit_v2 = cnt.get('mem_limit', None)
    mem_res_v2 = cnt.get('mem_reservation', None)
    # v3 < https://docs.docker.com/compose/compose-file/compose-file-v3/#resources
    # spec < https://github.com/compose-spec/compose-spec/blob/master/deploy.md#resources
    deploy = cnt.get('deploy', None) or {}
    res = deploy.get('resources', None) or {}
    limits = res.get('limits', None) or {}
    cpus_limit_v3 = try_float(limits.get('cpus', None), None)
    mem_limit_v3 = limits.get('memory', None)
    reservations = res.get('reservations', None) or {}
    #cpus_res_v3 = try_float(reservations.get('cpus', None), None)
    mem_res_v3 = reservations.get('memory', None)
    # add args
    cpus = cpus_limit_v3 or cpus_limit_v2
    if cpus:
        podman_args.extend(('--cpus', str(cpus),))
    if cpu_shares_v2:
        podman_args.extend(('--cpu-shares', str(cpu_shares_v2),))
    mem = mem_limit_v3 or mem_limit_v2
    if mem:
        podman_args.extend(('-m', str(mem).lower(),))
    mem_res = mem_res_v3 or mem_res_v2
    if mem_res:
        podman_args.extend(('--memory-reservation', str(mem_res).lower(),))

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
    if protocol!="tcp":
        ret+= f"/{protocol}"
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
        net_name = ext_desc.get("name", None) or net_desc.get("name", None) or default_net_name
        try: compose.podman.output([], "network", ["exists", net_name])
        except subprocess.CalledProcessError:
            if is_ext:
                raise RuntimeError(f"External network [{net_name}] does not exists")
            args = [
                "create",
                "--label", "io.podman.compose.project={}".format(proj_name),
                "--label", "com.docker.compose.project={}".format(proj_name),
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
            ipam_config_ls = (net_desc.get("ipam", None) or {}).get("config", None) or []
            if is_dict(ipam_config_ls):
                ipam_config_ls=[ipam_config_ls]
            for ipam in ipam_config_ls:
                subnet = ipam.get("subnet", None)
                ip_range = ipam.get("ip_range", None)
                gateway = ipam.get("gateway", None)
                if subnet: args.extend(("--subnet", subnet))
                if ip_range: args.extend(("--ip-range", ip_range))
                if gateway: args.extend(("--gateway", gateway))
            args.append(net_name)
            compose.podman.output([], "network", args)
            compose.podman.output([], "network", ["exists", net_name])

def get_net_args(compose, cnt):
    service_name = cnt["service_name"]
    net = cnt.get("network_mode", None)
    if net:
        if net=="host":
            return ['--network', net]
        if net.startswith("service:"):
            other_srv = net.split(":", 1)[1].strip()
            other_cnt = compose.container_names_by_service[other_srv][0]
            return ['--network', f"container:{other_cnt}"]
        if net.startswith("container:"):
            other_cnt = net.split(":",1)[1].strip()
            return ['--network', f"container:{other_cnt}"]
    proj_name = compose.project_name
    default_net = compose.default_net
    nets = compose.networks
    cnt_nets = cnt.get("networks", None)
    aliases = [service_name]
    # NOTE: from podman manpage:
    # NOTE: A container will only have access to aliases on the first network that it joins. This is a limitation that will be removed in a later release.
    ip = None
    if cnt_nets and is_dict(cnt_nets):
        for net_key, net_value in cnt_nets.items():
            aliases.extend(norm_as_list(net_value.get("aliases", None)))
            if ip: continue
            ip = net_value.get("ipv4_address", None)
        cnt_nets = list(cnt_nets.keys())
    cnt_nets = norm_as_list(cnt_nets or default_net)
    net_names = set()
    for net in cnt_nets:
        net_desc = nets[net] or {}
        is_ext = net_desc.get("external", None)
        ext_desc = is_ext if is_dict(is_ext) else {}
        default_net_name = net if is_ext else f"{proj_name}_{net}"
        net_name = ext_desc.get("name", None) or net_desc.get("name", None) or default_net_name
        net_names.add(net_name)
    net_names_str = ",".join(net_names)
    net_args = ["--net", net_names_str, "--network-alias", ",".join(aliases)]
    if ip:
        net_args.append(f"--ip={ip}")
    return net_args


def container_to_args(compose, cnt, detached=True):
    # TODO: double check -e , --add-host, -v, --read-only
    dirname = compose.dirname
    pod = cnt.get('pod', None) or ''
    podman_args = [
        '--name={}'.format(cnt.get('name', None)),
    ]

    if detached:
        podman_args.append("-d")

    if pod:
        podman_args.append('--pod={}'.format(pod))
    sec = norm_as_list(cnt.get("security_opt", None))
    for s in sec:
        podman_args.extend(['--security-opt', s])
    ann = norm_as_list(cnt.get("annotations", None))
    for a in ann:
        podman_args.extend(['--annotation', a])
    if cnt.get('read_only', None):
        podman_args.append('--read-only')
    for i in cnt.get('labels', []):
        podman_args.extend(['--label', i])
    for c in cnt.get('cap_add', []):
        podman_args.extend(['--cap-add', c])
    for c in cnt.get('cap_drop', []):
        podman_args.extend(['--cap-drop', c])
    for d in cnt.get('devices', []):
        podman_args.extend(['--device', d])
    env_file = cnt.get('env_file', [])
    if is_str(env_file): env_file = [env_file]
    for i in env_file:
        i = os.path.realpath(os.path.join(dirname, i))
        podman_args.extend(['--env-file', i])
    env = norm_as_list(cnt.get('environment', {}))
    for e in env:
        podman_args.extend(['-e', e])
    tmpfs_ls = cnt.get('tmpfs', [])
    if is_str(tmpfs_ls): tmpfs_ls = [tmpfs_ls]
    for i in tmpfs_ls:
        podman_args.extend(['--tmpfs', i])
    for volume in cnt.get('volumes', []):
        podman_args.extend(get_mount_args(compose, cnt, volume))

    assert_cnt_nets(compose, cnt)
    podman_args.extend(get_net_args(compose, cnt))

    log = cnt.get('logging')
    if log is not None:
        podman_args.append(f'--log-driver={log.get("driver", "k8s-file")}')
        log_opts = log.get('options') or {}
        podman_args += [f'--log-opt={name}={value}' for name, value in log_opts.items()]
    for secret in cnt.get('secrets', []):
        podman_args.extend(get_secret_args(compose, cnt, secret))
    for i in cnt.get('extra_hosts', []):
        podman_args.extend(['--add-host', i])
    for i in cnt.get('expose', []):
        podman_args.extend(['--expose', i])
    if cnt.get('publishall', None):
        podman_args.append('-P')
    ports = cnt.get('ports', None) or []
    if isinstance(ports, str):
        ports = [ports]
    for port in ports:
        if isinstance(port, dict):
            port = port_dict_to_str(port)
        elif not isinstance(port, str):
            raise TypeError("port should be either string or dict")
        podman_args.extend(['-p', port])

    user = cnt.get('user', None)
    if user is not None:
        podman_args.extend(['-u', user])
    if cnt.get('working_dir', None) is not None:
        podman_args.extend(['-w', cnt['working_dir']])
    if cnt.get('hostname', None):
        podman_args.extend(['--hostname', cnt['hostname']])
    if cnt.get('shm_size', None):
        podman_args.extend(['--shm-size', '{}'.format(cnt['shm_size'])])
    if cnt.get('stdin_open', None):
        podman_args.append('-i')
    if cnt.get('stop_signal', None):
        podman_args.extend(['--stop-signal', cnt['stop_signal']])
    for i in cnt.get('sysctls', []):
        podman_args.extend(['--sysctl', i])
    if cnt.get('tty', None):
        podman_args.append('--tty')
    if cnt.get('privileged', None):
        podman_args.append('--privileged')
    pull_policy = cnt.get('pull_policy', None)
    if pull_policy is not None and pull_policy!='build':
        podman_args.extend(['--pull', pull_policy])
    if cnt.get('restart', None) is not None:
        podman_args.extend(['--restart', cnt['restart']])
    container_to_ulimit_args(cnt, podman_args)
    container_to_res_args(cnt, podman_args)
    # currently podman shipped by fedora does not package this
    if cnt.get('init', None):
        podman_args.append('--init')
    if cnt.get('init-path', None):
        podman_args.extend(['--init-path', cnt['init-path']])
    entrypoint = cnt.get('entrypoint', None)
    if entrypoint is not None:
        if is_str(entrypoint):
            entrypoint = shlex.split(entrypoint)
        podman_args.extend(['--entrypoint', json.dumps(entrypoint)])

    # WIP: healthchecks are still work in progress
    healthcheck = cnt.get('healthcheck', None) or {}
    if not is_dict(healthcheck):
        raise ValueError("'healthcheck' must be an key-value mapping")
    healthcheck_test = healthcheck.get('test', None)
    if healthcheck_test:
        # If it's a string, it's equivalent to specifying CMD-SHELL
        if is_str(healthcheck_test):
            # podman does not add shell to handle command with whitespace
            podman_args.extend(['--healthcheck-command', '/bin/sh -c {}'.format(cmd_quote(healthcheck_test))])
        elif is_list(healthcheck_test):
            healthcheck_test = healthcheck_test.copy()
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

    podman_args.append(cnt['image'])  # command, ..etc.
    command = cnt.get('command', None)
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
                if ext != name: deps.add(ext)
                continue
        deps_ls = srv.get("depends_on", None) or []
        if is_str(deps_ls): deps_ls=[deps_ls]
        elif is_dict(deps_ls): deps_ls=list(deps_ls.keys())
        deps.update(deps_ls)
        # parse link to get service name and remove alias
        links_ls = srv.get("links", None) or []
        if not is_list(links_ls): links_ls=[links_ls]
        deps.update([(c.split(":")[0] if ":" in c else c)
            for c in links_ls])
    for name, srv in services.items():
        rec_deps(services, name)

