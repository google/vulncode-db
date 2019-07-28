# Vulncode-DB
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Overview
The vulnerable code database (Vulncode-DB) is a database for vulnerabilities and their corresponding 
source code if available. The database extends the NVD / CVE data sets with user-supplied 
information regarding patch links, vulnerable code offsets and descriptions.
Particularly, the database intends to make real-world examples of vulnerable code universally accessible and useful.

The main instance is hosted on [vulncode-db.com](https://www.vulncode-db.com) and more context is provided at [vulncode-db.com/about](https://www.vulncode-db.com/about).

**Please note:** 

This application is currently in an experimental alpha version mostly for demonstration purposes.
The application might be unreliable, contains many bugs and is not feature complete. Please set your expectations accordingly.


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
./docker/docker-admin.sh run
```

Additionally, if you intend to add some data consider running:
```
# Fetch and insert CWE identifiers and some recent NVD entries.
./docker/docker-admin.sh init
# Search for entries with patch links and add additional application entries for them.
./docker/docker-admin.sh crawl_patches
# Run the application.
./docker/docker-admin.sh run
```
The main application should then be available at `http://localhost:8080`.

Please also see the documentation provided in `docker/README.md` for more details.

## Terms of use

### Vulncode-DB Data

This project provides exclusive data such as vulnerability annotations and mappings from vulnerability entries to corresponding patches
and code. The terms of use apply to data provided through the website or implicitly through code in this repository.

```
Vulncode-DB hereby grants you a perpetual, worldwide, non-exclusive,
no-charge, royalty-free, irrevocable copyright license to reproduce, prepare
derivative works of, publicly display, publicly perform, sublicense, and
distribute data which is exclusively provided by Vulncode-DB. Any copy you make for
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