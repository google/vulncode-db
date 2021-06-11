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

# Attention: DO NOT DELETE THE * IMPORT BELOW
# -> Required to import all model definitions to allow database creation.

from typing import Dict, Iterable, Optional
from flask import Flask
from flask_migrate import Migrate  # type: ignore
from sqlalchemy.engine import reflection

from data.models import *  # pylint: disable=wildcard-import
from data.models.base import db, ma


class Database:
    db = db
    ma = ma  # pylint: disable=invalid-name
    migrate = Migrate(db=db)

    def __init__(self, app: Optional[Flask] = None):
        """Initializes the questionnaire object."""
        self.app = app

    def init_app(self, app: Flask):
        self.app = app
        with self.app.app_context():
            self.db.init_app(self.app)
            self.ma.init_app(self.app)
            self.migrate.init_app(self.app)

            # Create the database from all model definitions.
            # Note: This is a no-op if the tables already exist.
            # self.db.create_all()

    def reset_all(self):
        # Attention: This will drop the complete database with all its entries.
        self.db.drop_all()

        # Hack to remove all indices from the database...
        insp: reflection.Inspector = reflection.Inspector.from_engine(self.db.engine)
        table_names: Iterable[str] = insp.get_table_names()
        for name in table_names:
            indexes: Iterable[Dict[str, str]] = insp.get_indexes(name)
            for index in indexes:
                self.db.engine.execute(f"DROP INDEX IF EXISTS {index['name']}")
        self.app.logger.warning("!!! Attention !!! FLUSHED the main database.")

        # Create the database from all model definitions.
        self.db.create_all()

        self.db.session.commit()

    @property
    def session(self):
        return self.db.session

    def query(self, *args, **kwargs):
        return self.db.session.query(*args, **kwargs)


DEFAULT_DATABASE = Database()


def init_app(app: Flask):
    DEFAULT_DATABASE.init_app(app)
