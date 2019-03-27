# Vulncode-DB
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Overview
The vulnerable code database (Vulncode-DB) is a database for vulnerabilities and their corresponding 
source code if available. The database extends the NVD / CVE data sets with user-supplied 
information regarding patch links, vulnerable code offsets and descriptions.
Particularly, the database intends to make real-world examples of vulnerable code universally accessible and useful.


**Please note:** 

This application is currently in an experimental alpha version mostly for demonstration purposes.
The application might be unreliable, contains many bugs and is not feature complete. Please set your expectations accordingly.


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

## Setup
These are some vague instructions to setup this project on your own. A simplified docker container
setup will follow.

```
git clone https://github.com/google/vulncode-db

# Install Google's Cloud SDK. Follow steps on:
# See steps at: https://cloud.google.com/appengine/docs/standard/python/download and https://cloud.google.com/sdk/docs/#linux
# wget https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-239.0.0-linux-x86_64.tar.gz
# tar xfvz google-cloud-sdk-239.0.0-linux-x86_64.tar.gz
# ./google-cloud-sdk/install.sh
# Also make sure to run:
gcloud components install app-engine-python
gcloud components install app-engine-python-extras

# Note: If you don't use sudo here make sure to add ~/.local/bin to your $PATH variable.
sudo pip install virtualenv
virtualenv venv
source venv/bin/activate

# Install mysqldb Python connector libraries.
sudo apt install default-libmysqlclient-dev

# Install third party dependencies.
mkdir third_party
pip install -t third_party -r requirements.txt

# Install developer dependencies.
pip install -r dev_requirements.txt

# Setup a mysql database.
sudo apt install default-mysql-server
sudo mysql_secure_installation

# Mariadb uses a plugin for socket authentication by default.
# We can disable it in the following way.
echo "use mysql; update user set plugin='' where User='root'; flush privileges;" | sudo mysql -u root
# We should now be able to use mysql without sudo. You can test it with.
# mysql -u root -p

# Create required databases.
echo "CREATE DATABASE main; CREATE DATABASE cve; CREATE DATABASE cwe;" | sudo mysql -u root -p

# Setup and configure the application in app.yaml.
mv example_app.yaml app.yaml
# Edit app.yaml and 
# 1) Add the new mysql root password.
# 2) Fill out the remaining information.

# Init alembic migrations.
./manage.sh db init

# Test the application.
./run.sh
```

### Fetching CWE identifiers.
```
wget https://cwe.mitre.org/data/xml/views/2000.xml.zip
unzip 2000.xml.zip
grep -oP '(?<= ID=").*?" Name=".*?(?=")' 2000.xml | sed 's/" Name="/| /' | awk '{print "CWE-" $0}' > cwe.csv
# Import into database with.
echo "load data local infile 'cwe.csv' into table cwe.cwe_data fields terminated by '|' lines terminated by '\n' (cwe_id, cwe_name)" | sudo mysql -uroot -p 
```


### Importing NVD/CVE data.
Currently, this is a manual process using Docker and [go-cve-dictionary](https://github.com/kotakanbe/go-cve-dictionary).
```
git clone https://github.com/kotakanbe/go-cve-dictionary
cd go-cve-dictionary
# Reset to specific version in July 2018.
git reset --hard c2bcc418e037d6bc2d6b47c2d782900126b4f884
# Attention: Replace static.nvd.nist.gov with nvd.nist.gov as the application doesn't auto follow updated download urls.
sed -i 's/static.nvd.nist.gov/nvd.nist.gov/' nvd/nvd.go
# Build image
docker build -t go-cve-dictionary -f Dockerfile .
# Run image 
sudo docker run --network host -it --entrypoint /bin/sh go-cve-dictionary
# Import data into host mysql via:
go-cve-dictionary fetchnvd -dbtype mysql -dbpath "[username]:[password]@tcp(127.0.0.1:3306)/cve" -years 2019
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