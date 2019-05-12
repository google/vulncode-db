Build
-----
The contained core Docker services (see `docker-compose.yml`) are:
- vcs-proxy
- database
- frontend

They can be built and started with:
```
$ cd docker
$ docker-compose build
$ docker-compose up
```

More
---
Additional Docker services (see `docker-compose.admin.yml`) include:
- go-cve-dictionary - Fetching of NVD and CWE data.
- utils - Linting and formatting tools.
- tests-db - Ephemeral (using tmpfs) MySQL instance for test data.
- tests - Python runtime with relevant dependencies for test execution.

You can interact with all above services through `docker-admin.sh`:
```
$ cd docker
$ ./docker-admin.sh
```
This allows you to:
- Load data: latest CVE updates, this year's CVE data, full CVE data and CWE data.
- Execute unit tests contained in `/tests/`.
- Execute `crawl_patches` which will create Vulncode-DB entries from given NVD entries.
- Format the code with `eslint` and `yapf`.
- Lint the code with `eslint` and `pylint`.
- Get a shell inside a specific docker service.
