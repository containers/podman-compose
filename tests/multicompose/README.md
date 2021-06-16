# Multiple compose files

to make sure we get results similar to

```
docker-compose -f d1/docker-compose.yml -f d2/docker-compose.yml up -d
docker exec -ti d1_web1_1 sh -c 'set'
docker exec -ti d1_web2_1 sh -c 'set'
curl http://${d1_web1_1}:8001/index.txt
curl http://${d1_web1_1}:8002/index.txt
```

we need to verify

- project base directory and project name is `d1`
- `var12='d1/12.env'` which means `enf_file` was appended not replaced (which means that we normalize to array before merge)
- `var2='d1/2.env'` which means that paths inside `d2/docker-compose.yml` directory are relative to `d1`


