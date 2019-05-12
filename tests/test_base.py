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
"""Basis for all Flask related unit tests."""

import unittest
import os
import cfg
from lib.app_factory import create_app
from flask_migrate import upgrade as alembic_upgrade
from data.database import db

with open(os.path.join(cfg.BASE_DIR, "docker/db_schema.sql"), "rb") as f:
    _create_schemas_sql = f.read().decode("utf8")


class FlaskTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        test_config = {}
        test_config['TESTING'] = True
        test_config['WTF_CSRF_ENABLED'] = False
        test_config['DEBUG'] = True

        docker_db_uri = 'mysql+mysqldb://root:test_db_pass@tests-db:3306/main'
        test_config['SQLALCHEMY_DATABASE_URI'] = docker_db_uri
        app = create_app(test_config)
        cls.app = app
        cls.test_client = app.test_client()

        # Push one single global flask app context for usage.
        ctx = app.app_context()
        ctx.push()

        # Create all required schemas.
        db.engine.execute(_create_schemas_sql)
        # Create all data from the alembic migrations.
        alembic_upgrade()

    def setUp(self):
        pass

    def tearDown(self):
        pass
