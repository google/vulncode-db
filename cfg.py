#!/usr/bin/python
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
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Statement for enabling the development environment.
# Shows an interactive debugger for unhandled exceptions.
DEBUG = True

# Enables connecting to the remote database using port 3307 on cloud sql proxy.
USE_REMOTE_DB_THROUGH_CLOUDSQL_PROXY = False
# Proxy CloudSQL with
# ./cloud_sql_proxy -instances [MYSQL_CONNECTION_NAME]=tcp:3307
CLOUDSQL_PROXY_PORT = os.getenv('CLOUDSQL_PROXY_PORT', 3307)

IS_PROD = False
if os.getenv('SERVER_SOFTWARE', '').startswith('Google App Engine/'):
  IS_PROD = True

TITLE = 'Vulncode-DB'

# Used to process and proxy remote VCS content.
MYSQL_CONNECTION_NAME = os.environ['MYSQL_CONNECTION_NAME']
MYSQL_LOCAL_USER = os.environ['MYSQL_LOCAL_USER']
MYSQL_LOCAL_PASS = os.environ['MYSQL_LOCAL_PASS']
MYSQL_PROD_USER = os.environ['MYSQL_PROD_USER']
MYSQL_PROD_PASS = os.environ['MYSQL_PROD_PASS']

if IS_PROD:
  MYSQL_USER = MYSQL_PROD_USER
  GCE_VCS_PROXY_URL = os.environ['VCS_PROVIDER_URL']
else:
  MYSQL_USER = MYSQL_LOCAL_USER
  # Requires port forwarding with: ssh -L 8088:localhost:8080 [VCS_IP]
  GCE_VCS_PROXY_URL = 'https://localhost:8088/'


def gen_connection_string():
  # if not on Google then use local MySQL
  if IS_PROD:
    conn_template = 'mysql+mysqldb://%s:%s@localhost:3306/_DB_NAME_?unix_socket=/cloudsql/%s'
    return conn_template % (MYSQL_USER, MYSQL_PROD_PASS, MYSQL_CONNECTION_NAME)
  elif USE_REMOTE_DB_THROUGH_CLOUDSQL_PROXY:
    # Use Cloudsql through the cloudsql proxy.
    return ('mysql+mysqldb://root:%s@127.0.0.1:%d/_DB_NAME_' %
            (MYSQL_PROD_PASS, int(CLOUDSQL_PROXY_PORT)))
  else:
    # Use normal localhost database instance.
    return (
        'mysql+mysqldb://root:%s@127.0.0.1:3306/_DB_NAME_' % MYSQL_LOCAL_PASS)


SQLALCHEMY_DATABASE_URI = gen_connection_string().replace('_DB_NAME_', 'main')

SQLALCHEMY_ECHO = False
DATABASE_CONNECT_OPTIONS = {}
SQLALCHEMY_TRACK_MODIFICATIONS = False

SQLALCHEMY_BINDS = {
    'cwe': gen_connection_string().replace('_DB_NAME_', 'cwe'),
    'cve': gen_connection_string().replace('_DB_NAME_', 'cve')
}

# Application threads. A common general assumption is
# using 2 per available processor cores - to handle
# incoming requests using one and performing background
# operations using the other.
THREADS_PER_PAGE = 2

# Enable protection against *Cross-site Request Forgery (CSRF)*
CSRF_ENABLED = True

# Use a secure, unique and absolutely secret key for signing the data.
CSRF_SESSION_KEY = os.environ['CSRF_SESSION_KEY']

# Secret key for signing cookies
SECRET_KEY = os.environ['COOKIE_SECRET_KEY']

PATCH_REGEX = '.*(github\.com|\.git|\.patch|\/hg\.|\/\+\/)'

GOOGLE_OAUTH = {
    'consumer_key': os.environ['OAUTH_CONSUMER_KEY'],
    'consumer_secret': os.environ['OAUTH_CONSUMER_SECRET']
}

# Disable link intercepts for the Flask toolbar.
DEBUG_TB_INTERCEPT_REDIRECTS = False

# local overrides
try:
  from local_cfg import *
except ImportError:
  pass
