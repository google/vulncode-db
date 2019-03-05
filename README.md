# Vulncode-DB
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Overview
The vulnerable code database (Vulncode-DB) is a database for vulnerabilities and their corresponding 
source code if available. The database extends the NVD / CVE data sets with user-supplied 
information regarding patch links, vulnerable code offsets and descriptions.
Particularly, the database intends to make real-world examples of vulnerable code universally accessible and useful.


**Please note:** 

This is work in progress and **not yet properly usable**. Updates including critical bug fixes,
setup instructions and more will follow.


##  Directory structure
```
├── app
├── cert (SSL certificates)
├── data
│   ├── forms
│   └── models
├── lib
│   └── vcs_handler
├── static
│   ├── css
│   ├── js
│   │   └── lib
│   ├── monaco
│   │   └── themes
│   └── tutorial
├── templates
│   └── editor
├── third_party (third-party content)
└── vulnerable_code (temporary directory used for caching repositories)
```

## Third-party Data
This project builds upon data provided by the CVE and NVD data sets.

### Common Vulnerabilities and Exposures (CVE®)
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

### National Vulnerabilitiy Database (NVD)
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