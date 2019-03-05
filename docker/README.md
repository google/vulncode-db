Build
-----

```
$ cd docker
$ docker-compose build
```

or (from repository root)

```
$ docker build -t vcs-proxy -f docker/vcs_proxy/Dockerfile .
```

Run
---

```
$ docker-compose start
```

or 

```
$ docker run -p 8080:8080 -v path/to/cert:/proxy/cert --rm vcs-proxy
```
