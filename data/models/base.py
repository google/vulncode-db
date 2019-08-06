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

from flask_sqlalchemy import SQLAlchemy as SQLAlchemyBase
from flask_marshmallow import Marshmallow
from sqlalchemy import Index
from sqlalchemy.ext.declarative import declared_attr


# Adding the "pool_pre_ping" command to avoid mysql server has gone away issues.
# Note: This will slightly degrade performance. It might be better to adjust
#       MariaDB server settings.
class SQLAlchemy(SQLAlchemyBase):
    def apply_pool_defaults(self, app, options):
        super(SQLAlchemy, self).apply_pool_defaults(app, options)
        options["pool_pre_ping"] = True


db = SQLAlchemy()
ma = Marshmallow()


class MainBase(db.Model):
    # N.B. We leave the schema out on purpose as alembic gets confused otherwise.
    # The default schema is already main (as specified in the connection string).
    # Also see:
    # https://github.com/sqlalchemy/alembic/issues/519#issuecomment-442533633
    # __table_args__ = {'schema': 'main'}
    __abstract__ = True

    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    date_created = db.Column(db.DateTime, default=db.func.current_timestamp())
    date_modified = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )


class NvdBase(db.Model):
    __abstract__ = True

    @declared_attr
    def __table_args__(cls):
        indices = ()
        idx_format = "idx_{tbl_name}_{col_name}"
        for key in cls.__dict__:
            attribute = cls.__dict__[key]
            if not isinstance(attribute, db.Column) or not attribute.index:
                continue
            # Disable Index
            attribute.index = None
            # Create a custom index here.
            indices += (Index(
                idx_format.format(tbl_name=cls.__tablename__, col_name=key),
                key), )
        return indices + ({"schema": "cve"}, )


class CweBase(db.Model):
    __table_args__ = {"schema": "cwe"}
    __abstract__ = True
