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
import pytest
from lib.app_factory import create_app

DOCKER_DB_URI = 'mysql+mysqldb://root:test_db_pass@tests-db:3306/main'
TEST_CONFIG = {
    'TESTING': True,
    'WTF_CSRF_ENABLED': False,
    'DEBUG': True,
    'SQLALCHEMY_DATABASE_URI': None
}

@pytest.fixture
def app():
    app = create_app(TEST_CONFIG)
    return app

@pytest.fixture
def client(app):
    return app.test_client()


def test_index(client):
  resp = client.get('/')
  assert resp.status == 200