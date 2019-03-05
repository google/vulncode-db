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


# Adding the "pool_pre_ping" command to avoid mysql server has gone away issues.
# Note: This will slightly degrade performance. It might be better to adjust
#       MariaDB server settings.
class SQLAlchemy(SQLAlchemyBase):

  def apply_pool_defaults(self, app, options):
    super(SQLAlchemy, self).apply_pool_defaults(app, options)
    options["pool_pre_ping"] = True


db = SQLAlchemy()
ma = Marshmallow()

DefaultBase = db.Model


# Define a base model for other database tables to inherit
class Base(db.Model):

  __abstract__ = True

  id = db.Column(db.Integer, autoincrement=True, primary_key=True)
  date_created = db.Column(db.DateTime, default=db.func.current_timestamp())
  date_modified = db.Column(
      db.DateTime,
      default=db.func.current_timestamp(),
      onupdate=db.func.current_timestamp())
