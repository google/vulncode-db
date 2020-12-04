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
import datetime
import os
import logging
import contextlib

from flask import testing, appcontext_pushed, g
from flask_migrate import upgrade as alembic_upgrade

import requests
import pytest

import cfg

from data.database import DEFAULT_DATABASE
from data.models.user import User, Role, PredefinedRoles, UserState, LoginType
from data.models.vulnerability import Vulnerability, VulnerabilityState
from data.models.vulnerability import VulnerabilityGitCommits
from data.models.nvd import Cpe
from data.models.nvd import Nvd
from data.models.nvd import Reference
from data.models.nvd import Description
from lib.app_factory import create_app

DOCKER_DB_URI = "mysql+mysqldb://root:test_db_pass@tests-db:3306/main"
TEST_CONFIG = {
    "TESTING": True,
    "WTF_CSRF_ENABLED": False,
    "DEBUG": True,
    "SQLALCHEMY_DATABASE_URI": os.environ.get("SQLALCHEMY_DATABASE_URI", DOCKER_DB_URI),
    "SQLALCHEMY_ENGINE_OPTIONS": {
        "echo": False,  # log queries
        # 'echo_pool': True,  # log connections
    },
    "APPLICATION_ADMINS": ["admin@vulncode-db.com"],
    "IS_LOCAL": False,
    "RESTRICT_LOGIN": False,
}
# Used for integration tests against the production environment.
PROD_SERVER_URL = "https://www.vulncode-db.com"

log = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def app():
    app = create_app(TEST_CONFIG)
    # Establish an application context before running the tests.
    with app.app_context():
        yield app


@pytest.fixture
def client_without_db(app):
    # create a new app context to clear flask.g after requests finished
    with app.app_context():
        with app.test_client() as client:
            yield client


class ResponseWrapper:
    """
    This ensures that the requests.Response interface is consistent with what
    Werkzeug's response would look like.
    """

    def __init__(self, requests_response):
        """
        :param requests_response: requests.Response
        """
        self.response = requests_response

    def __getattr__(self, item):
        result = getattr(self.response, item)
        return result

    @property
    def data(self):
        return self.response.content


class RequestsClient(requests.Session):
    """
    This client provides a similar API to Flask's app.test_client().
    However, it uses Requests to actually execute valid requests against
    a given endpoint for example for integration tests against production.
    """

    def __init__(self, base):
        super().__init__()
        self.base_url = base

    def open(self, *args, **kwargs):
        return self.request(*args, **kwargs)

    def request(self, method, path, *args, **kwargs):
        if path.startswith("/"):
            url = self.base_url + path
        else:
            url = path
        response = super().request(method, url=url, *args, **kwargs)
        return ResponseWrapper(response)


# TODO: Make dynamic db_session fixture loading working here. We don't need any
#      valid database session for tests against the production environment.
#      Pytest doesn't seem to correctly load db_session when appending it to
#      fixturenames. This is mostly a performance issue for production tests.
@pytest.fixture
def client(request, db_session, client_without_db):
    # request.fixturenames.append('db_session')
    if request.config.getoption("-m") == "production":
        # Run production tests against the production service.
        requests_client = RequestsClient(PROD_SERVER_URL)
        yield requests_client
    else:
        # request.fixturenames.append('db_session')
        yield client_without_db


@pytest.fixture(scope="session")
def _db(app):
    """Returns session-wide initialised database."""
    db = app.extensions["sqlalchemy"].db

    # setup databases and tables
    with open(os.path.join(cfg.BASE_DIR, "docker/db_schema.sql"), "rb") as f:
        create_schemas_sql = f.read().decode("utf8")

    with app.app_context():
        # clear database
        db.drop_all()
        db.engine.execute("DROP TABLE IF EXISTS alembic_version")

        # build database
        db.engine.execute(create_schemas_sql)
        alembic_upgrade()

        # create data
        session = db.session
        roles = [
            Role(name=role) for role in (PredefinedRoles.ADMIN, PredefinedRoles.USER)
        ]
        session.add_all(roles)
        users = [
            User(
                login="admin@vulncode-db.com",
                full_name="Admin McAdmin",
                roles=roles,
                state=UserState.ACTIVE,
                login_type=LoginType.LOCAL,
            ),
            User(
                login="user@vulncode-db.com",
                full_name="User McUser",
                roles=[roles[1]],
                state=UserState.ACTIVE,
                login_type=LoginType.LOCAL,
            ),
            User(
                login="blocked@vulncode-db.com",
                full_name="Blocked User",
                roles=[roles[1]],
                state=UserState.BLOCKED,
                login_type=LoginType.LOCAL,
            ),
        ]
        session.add_all(users)

        vuln_cves = list("CVE-1970-{}".format(1000 + i) for i in range(10))
        new_cves = list("CVE-1970-{}".format(2000 + i) for i in range(10))
        cves = vuln_cves + new_cves

        nvds = []
        for i, cve in enumerate(cves, 1):
            nvds.append(
                Nvd(
                    cve_id=cve,
                    descriptions=[
                        Description(
                            value="Description {}".format(i),
                        ),
                    ],
                    references=[
                        Reference(
                            link="https://cve.mitre.org/cgi-bin/cvename.cgi?name={}".format(
                                cve
                            ),
                            source="cve.mitre.org",
                        ),
                    ],
                    published_date=datetime.date.today(),
                    cpes=[
                        Cpe(
                            vendor="Vendor {}".format(i),
                            product="Product {}".format(j),
                        )
                        for j in range(1, 4)
                    ],
                )
            )
        session.add_all(nvds)

        vulns = []
        for i, cve in enumerate(vuln_cves, 1):
            repo_owner = "OWNER"
            repo_name = "REPO{i}".format(i=i)
            repo_url = "https://github.com/{owner}/{repo}/".format(
                owner=repo_owner,
                repo=repo_name,
            )
            commit = "{:07x}".format(0x1234567 + i)
            vulns.append(
                Vulnerability(
                    vcdb_id=i,
                    cve_id=cve,
                    date_created=datetime.date.today(),
                    creator=users[1],
                    state=VulnerabilityState.PUBLISHED,
                    version=0,
                    comment="Vulnerability {} comment".format(i),
                    commits=[
                        VulnerabilityGitCommits(
                            commit_link="{repo_url}commit/{commit}".format(
                                repo_url=repo_url,
                                commit=commit,
                            ),
                            repo_owner=repo_owner,
                            repo_name=repo_name,
                            # TODO: test conflicting data?
                            repo_url=repo_url,
                            commit_hash=commit,
                        )
                    ],
                )
            )
        vulns.append(
            Vulnerability(
                state=VulnerabilityState.PUBLISHED,
                version=0,
                vcdb_id=len(vulns) + 1,
                cve_id="CVE-1970-1500",
                date_created=datetime.date.today(),
                comment="Vulnerability {} comment".format(len(vuln_cves) + 1),
                commits=[],
            )
        )
        session.add_all(vulns)

        session.commit()
    return db


def regular_user_info():
    user_info = {
        "email": "user@vulncode-db.com",
        "name": "User McUser",
        "picture": "https://google.com/",
        "type": "LOCAL",
    }
    return user_info


def admin_user_info():
    user_info = {
        "email": "admin@vulncode-db.com",
        "name": "Admin McAdmin",
        "picture": "https://google.com/",
        "type": "LOCAL",
    }
    return user_info


def blocked_user_info():
    user_info = {
        "email": "blocked@vulncode-db.com",
        "name": "Blocked User",
        "picture": "https://google.com/",
        "type": "LOCAL",
    }
    return user_info


def as_admin(client: testing.FlaskClient):
    ui = admin_user_info()
    with client.session_transaction() as session:
        session["user_info"] = ui

    user = User(full_name=ui["name"], login=ui["email"], profile_picture=ui["picture"])
    user.roles = [
        Role(name=PredefinedRoles.ADMIN),
        Role(name=PredefinedRoles.REVIEWER),
        Role(name=PredefinedRoles.USER),
    ]
    return user


def as_user(client: testing.FlaskClient):
    ui = regular_user_info()
    with client.session_transaction() as session:
        session["user_info"] = ui

    user = User(full_name=ui["name"], login=ui["email"], profile_picture=ui["picture"])
    user.roles = [
        Role(name=PredefinedRoles.USER),
    ]
    return user


@contextlib.contextmanager
def set_user(app, user):
    def handler(sender, **kwargs):
        g.user = user
        log.debug("Setting user %s", g.user)

    with appcontext_pushed.connected_to(handler, app):
        yield
