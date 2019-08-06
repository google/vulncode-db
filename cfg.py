#!/usr/bin/env python3
# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Statement for enabling the development environment.
# Shows an interactive debugger for unhandled exceptions.
# Attention: This will be disabled by default.
DEBUG = False

# Show a maintenance page.
MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"

# Enables connecting to the remote database using the cloud sql proxy.
USE_REMOTE_DB_THROUGH_CLOUDSQL_PROXY = (os.getenv(
    "USE_REMOTE_DB_THROUGH_CLOUDSQL_PROXY", "false").lower() == "true")

IS_PROD = IS_QA = IS_LOCAL = False
if os.getenv("GAE_ENV", "").startswith("standard"):
    # Running on GAE. This is either PROD or QA.
    appname = os.environ["GAE_APPLICATION"]
    appname = appname.replace('s~', '')

    if appname == os.environ["QA_PROJECT_ID"]:
        IS_QA = True
    elif appname == os.environ["PROD_PROJECT_ID"]:
        IS_PROD = True
    else:
        raise AssertionError(f"Deployed in unknown environment: {appname}.")

if not IS_PROD and not IS_QA:
    IS_LOCAL = True

# Make sure exactly one mode is active at all times.
assert int(IS_PROD) + int(IS_QA) + int(IS_LOCAL) == 1

if IS_PROD:
    DEBUG = False
    MYSQL_USER = os.environ["MYSQL_PROD_USER"]
    MYSQL_PASS = os.environ["MYSQL_PROD_PASS"]
    MYSQL_CONNECTION_NAME = os.environ["MYSQL_PROD_CONNECTION_NAME"]
    GCE_VCS_PROXY_URL = os.environ["VCS_PROXY_PROD_URL"]
elif IS_QA:
    DEBUG = True
    MYSQL_USER = os.environ["MYSQL_QA_USER"]
    MYSQL_PASS = os.environ["MYSQL_QA_PASS"]
    MYSQL_CONNECTION_NAME = os.environ["MYSQL_QA_CONNECTION_NAME"]
    GCE_VCS_PROXY_URL = os.environ["VCS_PROXY_QA_URL"]
elif IS_LOCAL:
    DEBUG = True
    MYSQL_USER = os.getenv("MYSQL_LOCAL_USER", "")
    MYSQL_PASS = os.getenv("MYSQL_LOCAL_PASS", "")
    GCE_VCS_PROXY_URL = os.getenv("VCS_PROXY_LOCAL_URL", "")
else:
    raise AssertionError("Invalid deployment mode detected.")


def gen_connection_string():
    # if not on Google then use local MySQL
    if IS_PROD or IS_QA:
        return f"mysql+mysqldb://{MYSQL_USER}:{MYSQL_PASS}@localhost:3306/_DB_NAME_?unix_socket=/cloudsql/{MYSQL_CONNECTION_NAME}"
    else:
        use_name = MYSQL_USER
        use_pass = MYSQL_PASS
        use_host = "127.0.0.1"
        use_port = 3306
        if "MYSQL_HOST" in os.environ:
            use_host = os.environ["MYSQL_HOST"]
        elif "MYSQL_LOCAL_PORT" in os.environ:
            use_port = int(os.environ["MYSQL_LOCAL_PORT"])

        if USE_REMOTE_DB_THROUGH_CLOUDSQL_PROXY:
            use_name = os.environ["CLOUDSQL_NAME"]
            use_pass = os.environ["CLOUDSQL_PASS"]
            use_port = int(os.getenv("CLOUDSQL_PORT", 3307))
        return f"mysql+mysqldb://{use_name}:{use_pass}@{use_host}:{use_port}/_DB_NAME_"


SQLALCHEMY_DATABASE_URI = gen_connection_string().replace("_DB_NAME_", "main")

SQLALCHEMY_ECHO = False
DATABASE_CONNECT_OPTIONS = {}
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Application threads. A common general assumption is
# using 2 per available processor cores - to handle
# incoming requests using one and performing background
# operations using the other.
THREADS_PER_PAGE = 2

# Enable protection against *Cross-site Request Forgery (CSRF)*
CSRF_ENABLED = True

# Use a secure, unique and absolutely secret key for signing the data.
CSRF_SESSION_KEY = os.getenv("CSRF_SESSION_KEY", "")

# Secret key for signing cookies
SECRET_KEY = os.getenv("COOKIE_SECRET_KEY", "")

PATCH_REGEX = r".*(github\.com|\.git|\.patch|\/hg\.|\/\+\/)"

GOOGLE_OAUTH = {
    "consumer_key": os.getenv("OAUTH_CONSUMER_KEY", ""),
    "consumer_secret": os.getenv("OAUTH_CONSUMER_SECRET", "")
}

# Make sure relevant properties are always set for QA and PROD.
if IS_PROD or IS_QA:
    assert len(CSRF_SESSION_KEY) > 0
    assert len(SECRET_KEY) > 0
    assert len(GOOGLE_OAUTH["consumer_key"]) > 0
    assert len(GOOGLE_OAUTH["consumer_secret"]) > 0

# Emails (checked with OAuth) of admins who are allowed to make admin changes.
APPLICATION_ADMINS = os.getenv("APPLICATION_ADMINS", "").replace(" ", "")
APPLICATION_ADMINS = APPLICATION_ADMINS.split(",")

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# Disable link intercepts for the Flask toolbar.
DEBUG_TB_INTERCEPT_REDIRECTS = False

# We use certificate pinning to ensure correct communication between components.
APP_CERT_FILE = "cert/cert.pem"

# local overrides
try:
    from local_cfg import *
except ImportError:
    pass
