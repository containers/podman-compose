#! /usr/bin/env python


# https://docs.docker.com/compose/compose-file/#service-configuration-reference
# https://docs.docker.com/samples/
# https://docs.docker.com/compose/gettingstarted/
# https://docs.docker.com/compose/django/
# https://docs.docker.com/compose/wordpress/

from __future__ import print_function


import os
import argparse
import subprocess
import time
import fnmatch

# fnmatch.fnmatchcase(env, "*_HOST")

import json
import yaml

# helpers

def try_int(i, fallback=None):
    try: return int(i)
    except ValueError: pass
    except TypeError: pass
    return fallback

def norm_as_list(src):
    """
    given a dictionary {key1:value1, key2: None} or list
    return a list of ["key1=value1", "key2"]
    """
    if src is None:
        dst=[]
    elif isinstance(src, dict):
        dst=[("{}={}".format(k, v) if v else k) for k,v in src.items()]
    elif hasattr(src, '__iter__'):
        dst=list(src)
    else:
        dst=[src]
    return dst

def norm_as_dict(src):
    """
    given a list ["key1=value1", "key2"]
    return a dictionary {key1:value1, key2: None}
    """
    if src is None:
        dst={}
    elif isinstance(src, dict):
        dst=dict(src)
    elif hasattr(src, '__iter__'):
        dst=[ i.split("=", 1) for i in src if i ]
        dst=dict([ (a if len(a)==2 else (a[0], None)) for a in dst ])
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
        if len(a)==2:
            alias=a[1].strip()
            extra_hosts.append("{}:{}".format(alias, dst))
    cnt["extra_hosts"] = extra_hosts

def move_port_fw(dst, containers):
    """
    move port forwarding from containers to dst (a pod or a infra container)
    """
    ports=dst.get("ports") or []
    for cnt in containers:
        cnt_ports = cnt.get('ports')
        if cnt_ports:
            ports.extend(cnt_ports)
            del cnt['ports']
    if ports: dst["ports"]=ports

# transformations

transformations={}
def trans(func):
    transformations[func.__name__.replace("tr_", "")]=func
    return func

@trans
def tr_identity(project_name, services, given_containers):
    containers=[]
    for cnt in given_containers:
        containers.append(dict(cnt))
    return [], containers

@trans
def tr_publishall(project_name, services, given_containers):
    containers=[]
    for cnt0 in given_containers:
        cnt=dict(cnt0, publishall=True)
        # adjust hosts to point to the gateway, TODO: adjust host env
        adj_hosts(services, cnt, '10.0.2.2')
        containers.append(cnt)
    return [], containers

@trans
def tr_hostnet(project_name, services, given_containers):
    containers=[]
    for cnt0 in given_containers:
        cnt=dict(cnt0, network_mode="host")
        # adjust hosts to point to localhost, TODO: adjust host env
        adj_hosts(services, cnt, '127.0.0.1')
        containers.append(cnt)
    return [], containers

@trans
def tr_cntnet(project_name, services, given_containers):
    containers=[]
    infra_name=project_name+"_infra"
    infra = dict(
        name=infra_name,
        image="k8s.gcr.io/pause:3.1",
    )
    for cnt0 in given_containers:
        cnt=dict(cnt0, network_mode="container:"+infra_name)
        deps=cnt.get("depends") or []
        deps.append(infra_name)
        dnt["depends"]=deps
        # adjust hosts to point to localhost, TODO: adjust host env
        adj_hosts(services, cnt, '127.0.0.1')
        # TODO: do we need to move port publishing to infra
        containers.append(cnt)
    move_port_fw(infra, containers)
    containers.insert(0, infra)
    return [], containers

@trans
def tr_1pod(project_name, services, given_containers):
    """
    project_name: 
    services: {service_name: ["container_name1", "..."]}, currently only one is supported
    given_containers: [{}, ...]
    """
    pod=dict(name=project_name)
    containers=[]
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
    pod=pods[0]
    move_port_fw(pod, containers)
    return pods, containers

def down(project_name, dirname, pods, containers):
    for cnt in containers:
        cmd="""podman stop -t=1 '{name}'""".format(**cnt)
        print(cmd)
        subprocess.Popen(cmd, shell=True).wait()
    for cnt in containers:
        cmd="""podman rm '{name}'""".format(**cnt)
        print(cmd)
        subprocess.Popen(cmd, shell=True).wait()
    for pod in pods:
        cmd="""podman pod rm '{name}'""".format(**pod)
        print(cmd)
        subprocess.Popen(cmd, shell=True).wait()

def container_to_args(cnt, dirname):
    pod=cnt.get('pod') or ''
    args=[
      'podman', 'run',
      '--name={}'.format(cnt.get('name')),
      '-d'
    ]
    if pod:
        args.append('--pod={}'.format(pod))
    if cnt.get('read_only'):
        args.append('--read-only')
    for i in cnt.get('labels', []):
        args.extend(['--label', i])
    net=cnt.get("network_mode")
    if net:
        args.extend(['--network', net])
    env=norm_as_list(cnt.get('environment', {}))
    for e in env:
        args.extend(['-e', e])
    for i in cnt.get('env_file', []):
        i=os.path.realpath(os.path.join(dirname, i))
        args.extend(['--env-file', i])
    for i in cnt.get('tmpfs', []):
        args.extend(['--tmpfs', i])
    for i in cnt.get('volumes', []):
        # TODO: make it absolute using os.path.realpath(i)
        args.extend(['-v', i])
    for i in cnt.get('extra_hosts', []):
        args.extend(['--add-host', i])
    for i in cnt.get('expose', []):
        args.extend(['--expose', i])
    if cnt.get('publishall'):
        args.append('-P')
    for i in cnt.get('ports', []):
        args.extend(['-p', i])
    user=cnt.get('user')
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
    #if cnt.get('init'):
    #    args.append('--init')
    entrypoint = cnt.get('entrypoint')
    if entrypoint is not None:
        if isinstance(entrypoint, list):
            args.extend(['--entrypoint', json.dumps(entrypoint)])
        else:
            args.extend(['--entrypoint', entrypoint])
    args.append(cnt.get('image')) # command, ..etc.
    command=cnt.get('command')
    if command is not None:
        # TODO: handle if command is string
        args.extend(command)
    return args

def up(project_name, dirname, pods, containers):
    os.chdir(dirname)
    # no need remove them if they have same hash label
    down(project_name, dirname, pods, containers)
    for pod in pods:
      args=[
        "podman", "pod", "create",
        "--name={}".format(pod["name"]),
        "--share", "cgroup,uts",
      ]
      ports = pod.get("ports") or []
      for i in ports:
          args.extend(['-p', i])
      print(" ".join(args))
      p=subprocess.Popen(args)
      print(p.wait())
    #print(opts)
    for cnt in containers:
        # TODO: -e , --add-host, -v, --read-only
        args = container_to_args(cnt, dirname)
        print(" ".join(args))
        p=subprocess.Popen(args)
        print(p.wait())
        #print("""podman run -d --pod='{pod}' --name='{name}' '{image}'""".format(**cnt))
        # subprocess.Popen(args, bufsize=0, executable=None, stdin=None, stdout=None, stderr=None, preexec_fn=None, close_fds=False, shell=False, cwd=None, env=None, universal_newlines=False, startupinfo=None, creationflags=0)
    time.sleep(3600)

def main(filename, project_name, no_ansi, transform_policy, host_env=None):
    filename= os.path.realpath(filename)
    dirname = os.path.dirname(filename)
    dir_basename = os.path.basename(dirname)
    if not project_name: project_name = dir_basename
    with open(filename, 'r') as f:
        compose=yaml.safe_load(f)
    print(json.dumps(compose, indent=2))
    ver=compose.get('version')
    services=compose.get('services')
    podman_compose_labels=[
      "io.podman.compose.config-hash=123",
      "io.podman.compose.project="+project_name,
      "io.podman.compose.version=0.0.1",
    ]
    # other top-levels:
    # volumes: {...}
    # networks: {driver: ...}
    # configs: {...}
    # secrets: {...}
    given_containers = []
    container_names_by_service = {}
    for service_name, service_desc in services.items():
        replicas = try_int(service_desc.get('deploy', {}).get('replicas', '1'))
        container_names_by_service[service_name]=[]
        for num in range(1, replicas+1):
            name = "{project_name}_{service_name}_{num}".format(
              project_name=project_name,
              service_name=service_name,
              num=num,
            )
            container_names_by_service[service_name].append(name)
            #print(service_name,service_desc)
            cnt=dict(name=name, num=num, service_name=service_name, **service_desc)
            labels = norm_as_list(cnt.get('labels'))
            labels.extend(podman_compose_labels)
            labels.extend([
                "com.docker.compose.container-number={}".format(num),
                "com.docker.compose.service="+service_name,
            ])
            cnt['labels'] = labels
            given_containers.append(cnt)
    tr=transformations[transform_policy]
    pods, containers = tr(project_name, container_names_by_service, given_containers)
    up(project_name, dirname, pods, containers)


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument('command', metavar='command',
      help='command to run',
      choices=['up', 'down'], nargs=1, default="up")

  parser.add_argument("-f", "--file",
      help="Specify an alternate compose file (default: docker-compose.yml)",
      type=str, default='docker-compose.yml')
  parser.add_argument("-p", "--project-name",
      help="Specify an alternate project name (default: directory name)",
      type=str, default=None)
  parser.add_argument("--no-ansi",
      help="Do not print ANSI control characters", action='store_true')
  
  parser.add_argument("-t", "--transform_policy",
      help="how to translate docker compose to podman [1pod|hostnet|accurate]",
      choices=['1pod', '1podfw', 'hostnet', 'cntnet', 'publishall', 'identity'], default='1podfw')

  args = parser.parse_args()

  main(
    filename=args.file,
    project_name=args.project_name,
    no_ansi=args.no_ansi,
    transform_policy=args.transform_policy)
