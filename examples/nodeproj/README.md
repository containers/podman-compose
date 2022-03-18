# How to run example



```
cp example.local.env local.env
cp example.env .env
cat local.env
cat .env
echo "UID=$UID" >> .env
cat .env
podman-compose build
podman-compose run --rm --no-deps init
podman-compose up
```

