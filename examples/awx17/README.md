# AWX Compose

The directory roles is taken from [here](https://github.com/ansible/awx/tree/17.1.0/installer/roles/local_docker)

also look at https://github.com/ansible/awx/tree/17.1.0/tools/docker-compose

```
mkdir deploy awx17
ansible localhost \
    -e host_port=8080 \
    -e awx_secret_key='awx,secret.123' \
    -e secret_key='awx,secret.123' \
    -e admin_user='admin' \
    -e admin_password='admin' \
    -e pg_password='awx,123.' \
    -e pg_username='awx' \
    -e pg_database='awx' \
    -e pg_port='5432' \
    -e redis_image="docker.io/library/redis:6-alpine" \
    -e postgres_data_dir="./data/pg" \
    -e compose_start_containers=false \
    -e dockerhub_base='docker.io/ansible' \
    -e awx_image='docker.io/ansible/awx' \
    -e awx_version='17.1.0' \
    -e dockerhub_version='17.1.0' \
    -e docker_deploy_base_path=$PWD/deploy \
    -e docker_compose_dir=$PWD/awx17 \
    -e awx_task_hostname=awx \
    -e awx_web_hostname=awxweb \
    -m include_role -a name=local_docker
cp awx17/docker-compose.yml awx17/docker-compose.yml.orig
sed -i -re "s#- \"$PWD/awx17/(.*):/#- \"./\1:/#" awx17/docker-compose.yml
cd awx17
podman-compose run --rm --service-ports task awx-manage migrate --no-input
podman-compose up -d
```

