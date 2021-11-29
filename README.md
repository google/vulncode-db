# Vulncode-DB
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Deprecation notice
**Note:** This project will be discontinued after **December 13th, 2021**.

## Overview
The vulnerable code database (Vulncode-DB) is a database for vulnerabilities and their corresponding 
source code if available. The database extends the NVD / CVE data sets with user-supplied 
information regarding patch links, vulnerable code offsets and descriptions.
Particularly, the database intends to make real-world examples of vulnerable code universally accessible and useful.

The main instance is hosted on [vulncode-db.com](https://www.vulncode-db.com) and more context is provided at [vulncode-db.com/about](https://www.vulncode-db.com/about).

### Why is this project deprecated?
- **Bootstrapping problem** - Vulncode-DB 's usefulness depends on having unique content. We can automatically detect some vulnerability patches via CVE/NVD metadata. We can also highlight relevant sections and annotate them in a write-up fashion. We also allow users to modify or annotate content themselves. However, this by itself is insufficient to make anyone use the platform. You need much and high-quality data first to make this useful, which a prototype like ours can't attain at this stage without extensive investment.
- **Lack of community support** - While there was some positive feedback there have been only a few contributors. The platform and vision seem to be inadequate to get more practical support.
- **Insufficient resources** - Developing the platform and for example a feature like a version control system for user moderated content similar to Wikipedia requires much engineering work for which we, as 20% contributors, are understaffed.
- **Added value unknown** - Even if all of the above would be solved it's still unclear whether the platform would provide sufficient value for individuals to justify a dedicated project. You can go to CVE details or Google for write-ups to learn more about a vulnerability. This is an established habit, hard to break and might already be good enough for individuals to learn more.

### How and when?
- This repository will be kept alive. However, we'll discontinue the [https://vulncode-db.com](https://vulncode-db.com) website and API after **December 13th, 2021**.

### Do you have feedback/ideas for how it should be continued?
- We're open to feedback, let's talk! You can reach us via [https://twitter.com/evonide](https://twitter.com/evonide) (rhabalov [at] gmail.com) or [https://twitter.com/bluec0re](https://twitter.com/bluec0re).

Finally, thank you to all contributors and individuals who supported the project. We are very grateful for your support, time and feedback.

Best,

Ruslan and Timo



##  Directory structure
```
├── app
│   └── [submodules with Flask routes and views]
├── cert (SSL certificates)
├── data
│   ├── forms
│   └── models (Database models)
├── docker (Docker files)
├── lib (helping libraries)
│   └── vcs_handler
├── migrations (Flask-Migrate / Alembic files)
├── static (CSS, JS and other static files)
│   ├── css
│   ├── js
│   │   └── lib
│   ├── monaco
│   │   └── themes
│   └── tutorial
├── templates (Jinja2 templates)
│   └── editor
│   └── macros
├── tests (Unit tests)
├── third_party (Third-party content)
└── vulnerable_code (Temporary directory used for caching repositories)
```

## Setup
The setup is simplified with Docker and docker-compose in particular. Having these prerequisites installed you can setup
 the project using the following instructions:
 
```
# Clone the repository and its (third-party) submodules.
git clone --recursive https://github.com/google/vulncode-db.git
cd vulncode-db
# Setup configuration files, the Docker images and containers.
./setup.sh
# Initialize the application and run an empty version of it.
./docker/docker-admin.sh start
```

Additionally, if you intend to add some data consider running:
```
# Fetch and insert CWE identifiers and some recent NVD entries.
./docker/docker-admin.sh init
# Search for entries with patch links and add additional application entries for them.
./docker/docker-admin.sh crawl_patches
# Run the application.
./docker/docker-admin.sh start
```
The main application should then be available at `http://localhost:8080`.

Please also see the documentation provided in `docker/README.md` for more details.

## Terms of use

### Vulncode-DB Data

This project provides data such as vulnerability annotations and mappings from vulnerability entries to corresponding patches
and code. It can be self-hosted or accessed through the main project site at https://vulncode-db.com.

For any user provided content on the project's website we refer to the terms of conditions provided within this repository.
Otherwise, for the project's code itself:
```
Vulncode-DB hereby grants you a perpetual, worldwide, non-exclusive,
no-charge, royalty-free, irrevocable copyright license to reproduce, prepare
derivative works of, publicly display, publicly perform, sublicense, and
distribute code which exclusively provided by the Vulncode-DB project. Any copy you make for
such purposes is authorized provided that you reproduce Vulncode-DB's copyright
designation and this license in any such copy.
```

### Third-party Data
This project builds upon data provided by the CVE and NVD data sets.

#### Common Vulnerabilities and Exposures (CVE®)
The [CVE®](https://cve.mitre.org/) is maintained by the Mitre Corporation.
Please see the Mitre CVE®'s [Terms of use](https://cve.mitre.org/about/termsofuse.html):
```
CVE Usage: MITRE hereby grants you a perpetual, worldwide, non-exclusive,
no-charge, royalty-free, irrevocable copyright license to reproduce, prepare
derivative works of, publicly display, publicly perform, sublicense, and
distribute Common Vulnerabilities and Exposures (CVE®). Any copy you make for
such purposes is authorized provided that you reproduce MITRE's copyright
designation and this license in any such copy.
```

#### National Vulnerabilitiy Database (NVD)
The [National Vulnerability Database](https://nvd.nist.gov/) is maintained by the U.S. government.
Please see the NVD's [FAQ](https://nvd.nist.gov/general/faq#1f2488ea-0492-45a7-ae5b-ad29bc31dd05):
```
All NVD data is freely available from our XML Data Feeds. There are no fees,
licensing restrictions, or even a requirement to register. All NIST
publications are available in the public domain according to Title 17 of the
United States Code. Acknowledgment of the NVD  when using our information is
appreciated. In addition, please email nvd@nist.gov to let us know how the
information is being used.
```

## Disclaimer
**This is not an officially supported Google product.**