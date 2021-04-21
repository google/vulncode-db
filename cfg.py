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
# pylint: disable=line-too-long

import os
import logging
import logging.handlers
from typing import List

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
USE_REMOTE_DB_THROUGH_CLOUDSQL_PROXY = (
    os.getenv("USE_REMOTE_DB_THROUGH_CLOUDSQL_PROXY", "false").lower() == "true"
)

IS_PROD = IS_QA = IS_LOCAL = False
if os.getenv("GAE_ENV", "").startswith("standard"):
    # Running on GAE. This is either PROD or QA.
    appname = os.environ["GAE_APPLICATION"]
    appname = appname.replace("s~", "")

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
    MYSQL_USER = os.getenv("MYSQL_LOCAL_USER", "root")
    MYSQL_PASS = os.getenv("MYSQL_LOCAL_PASS", "pass")
    GCE_VCS_PROXY_URL = os.getenv("VCS_PROXY_LOCAL_URL", "")
else:
    raise AssertionError("Invalid deployment mode detected.")

PROD_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def gen_connection_string():
    # if not on Google then use local MySQL
    if IS_PROD or IS_QA:
        return (
            f"mysql+mysqldb://{MYSQL_USER}:{MYSQL_PASS}@localhost:3306"
            f"/_DB_NAME_?unix_socket=/cloudsql/{MYSQL_CONNECTION_NAME}"
        )

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
        use_port = int(os.getenv("CLOUDSQL_PORT", "3307"))
    return f"mysql+mysqldb://{use_name}:{use_pass}@{use_host}:{use_port}" "/_DB_NAME_"


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

GOOGLE_CLIENT_ID = os.getenv(
    "GOOGLE_OAUTH_CONSUMER_KEY", os.getenv("OAUTH_CONSUMER_KEY", "")
)
GOOGLE_CLIENT_SECRET = os.getenv(
    "GOOGLE_OAUTH_CONSUMER_SECRET", os.getenv("OAUTH_CONSUMER_SECRET", "")
)
GITHUB_CLIENT_ID = os.getenv("GITHUB_OAUTH_CONSUMER_KEY", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_OAUTH_CONSUMER_SECRET", "")

# Make sure relevant properties are always set for QA and PROD.
if IS_PROD or IS_QA:
    assert len(CSRF_SESSION_KEY) > 0
    assert len(SECRET_KEY) > 0
    assert len(GOOGLE_CLIENT_ID) > 0
    assert len(GOOGLE_CLIENT_SECRET) > 0

# Emails (checked with OAuth) of admins who are allowed to make admin changes.
suggested_admins = os.getenv("APPLICATION_ADMINS", "").replace(" ", "")
APPLICATION_ADMINS: List[str] = []
if suggested_admins != "":
    APPLICATION_ADMINS = suggested_admins.split(",")

# Restrict the login to administrators only.
RESTRICT_LOGIN = os.getenv("RESTRICT_LOGIN", "true").lower() == "true"

# Registration mode can be CLOSED, INVITE_ONLY or OPEN.
REGISTRATION_MODE = os.getenv("REGISTRATION_MODE", "INVITE_ONLY").upper()
if REGISTRATION_MODE not in ["CLOSED", "INVITE_ONLY", "OPEN"]:
    raise AssertionError("Invalid REGISTRATION_MODE passed.")

AUTO_ENABLE_INVITED_USERS = True

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# Disable link intercepts for the Flask toolbar.
DEBUG_TB_INTERCEPT_REDIRECTS = False

# We use certificate pinning to ensure correct communication between
# components.
APP_CERT_FILE = "cert/cert.pem"


class clsproperty(property):  # pylint: disable=invalid-name
    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()  # pylint: disable=no-member


class __lazy:  # pylint: disable=invalid-name
    @clsproperty
    @classmethod
    def root_level(cls):
        return logging.DEBUG if DEBUG else logging.INFO


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "basic",
            "level": logging.NOTSET,
            "stream": "ext://sys.stdout",
        },
        "console_mini": {
            "class": "logging.StreamHandler",
            "formatter": "minimalistic",
            "level": logging.NOTSET,
            "stream": "ext://sys.stdout",
        },
        "info_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "full",
            "filename": os.path.join(BASE_DIR, "info.log"),
            "maxBytes": 100000,
            "backupCount": 1,
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "full",
            "filename": os.path.join(BASE_DIR, "error.log"),
            "maxBytes": 100000,
            "backupCount": 1,
            "level": logging.WARNING,
        },
    },
    "formatters": {
        "minimalistic": {
            "format": "%(message)s",
        },
        "basic": {
            "format": "%(levelname)-4.4s [%(name)s] %(message)s",
        },
        "full": {
            "format": "%(asctime)s - %(levelname)-4.4s [%(name)s,%(filename)s:%(lineno)d] %(message)s",
        },
    },
    "loggers": {
        "": {
            "level": "ext://cfg.__lazy.root_level",
            "handlers": ["console", "error_file", "info_file"],
        },
        "werkzeug": {
            "handlers": ["console_mini"],
            "propagate": False,
        },
    },
}

# local overrides
try:
    # pylint: disable=wildcard-import
    from local_cfg import *

    # pylint: enable=wildcard-import
except ImportError:
    pass
