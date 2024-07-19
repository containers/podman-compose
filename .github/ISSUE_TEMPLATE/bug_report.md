---
name: Bug report
about: Create a report to help us improve
title: ''
labels: bug
assignees: ''

---

**Describe the bug**
A clear and concise description of what the bug is.

Please make sure it's not a bug in podman (in that case report it to podman)
or your understanding of docker-compose or how rootless containers work (for example, it's normal for rootless container not to be able to listen for port less than 1024 like 80)

**To Reproduce**
Steps to reproduce the behavior:
1. what is the content of the current working directory (ex. `docker-compose.yml`, `.env`, `Dockerfile`, ...etc.)
2. what is the sequence of commands you typed

please use [minimal reproducible example](https://stackoverflow.com/help/minimal-reproducible-example) for example give me a small busybox-based compose yaml


**Expected behavior**
A clear and concise description of what you expected to happen.

**Actual behavior**
What is the behavior you actually got and that should not happen.


**Output**

```
$ podman-compose version
using podman version: 3.4.0
podman-compose version  0.1.7dev
podman --version 
podman version 3.4.0

$ podman-compose up
...

```

**Environment:**
 - OS: Linux / WSL / Mac
 - podman version: 
 - podman compose version: (git hex)

**Additional context**

Add any other context about the problem here.
