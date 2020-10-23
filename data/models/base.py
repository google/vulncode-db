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
from typing import Dict, Tuple, Any, TYPE_CHECKING
from itertools import zip_longest
import logging

from flask_sqlalchemy import SQLAlchemy as SQLAlchemyBase  # type: ignore
from flask_sqlalchemy import DefaultMeta
from flask_marshmallow import Marshmallow  # type: ignore
from sqlalchemy import Index, Column, Integer, func, DateTime, inspect
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapper, RelationshipProperty

log = logging.getLogger(__name__)


# Adding the "pool_pre_ping" command to avoid mysql server has gone away issues.
# Note: This will slightly degrade performance. It might be better to adjust
#       MariaDB server settings.
class SQLAlchemy(SQLAlchemyBase):
    def apply_pool_defaults(self, app, options):
        super(SQLAlchemy, self).apply_pool_defaults(app, options)
        options["pool_pre_ping"] = True


db = SQLAlchemy()
ma = Marshmallow()  # pylint: disable=invalid-name

BaseModel: DefaultMeta = db.Model


class MainBase(BaseModel):
    # N.B. We leave the schema out on purpose as alembic gets confused
    # otherwise. The default schema is already main (as specified in the
    # connection string). Also see:
    # https://github.com/sqlalchemy/alembic/issues/519#issuecomment-442533633
    # __table_args__ = {'schema': 'main'}
    __abstract__ = True

    id = Column(Integer, autoincrement=True, primary_key=True)
    date_created = Column(DateTime, default=func.current_timestamp())
    date_modified = Column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    def diff(self,
             other: BaseModel,
             *,
             already_tested=None) -> Dict[str, Tuple[Any, Any]]:
        changes = {}
        if already_tested is None:
            already_tested = {id(self), id(other)}
        elif id(self) in already_tested and id(other) in already_tested:
            return changes
        already_tested.add(id(self))
        already_tested.add(id(other))
        clz = type(self)
        oclz = type(other)
        if not isinstance(other, clz):
            raise TypeError("Instance of {} expected. Got {}".format(
                clz.__name__, oclz.__name__))

        def innerdiff(current, other):
            if current is None and other is None:
                return None
            elif current is None or other is None:
                return (current, other)
            elif hasattr(current, 'diff'):
                return current.diff(other, already_tested=already_tested)
            elif isinstance(current, list) and isinstance(other, list):
                res = []
                for c, o in zip_longest(current, other):
                    res.append(innerdiff(c, o))
                return res
            elif current != other:
                return (cv, ov)

        m: Mapper = inspect(clz)
        for name, attr in m.attrs.items():
            # log.debug('Compare %s of %s <> %s', name, clz, oclz)
            ov = getattr(other, name)
            cv = getattr(self, name)

            if name == 'resources':
                breakpoint()

            if isinstance(attr, RelationshipProperty):
                for c in attr.local_columns:
                    cname = c.name
                    if innerdiff(getattr(self, cname), getattr(other, cname)):
                        break
                else:
                    continue
                if name in changes:
                    continue
            c = innerdiff(cv, ov)
            if c:
                changes[name] = c

        return changes


class NvdBase(BaseModel):
    __abstract__ = True

    @declared_attr
    def __table_args__(cls):  # pylint: disable=no-self-argument
        indices = []
        idx_format = "idx_{tbl_name}_{col_name}"
        for key in cls.__dict__:
            attribute = cls.__dict__[key]
            # pylint: disable=no-member
            if not isinstance(attribute, db.Column) or not attribute.index:
                continue
            # pylint: enable=no-member

            # Disable Index
            attribute.index = None
            # Create a custom index here.
            indices.append(
                Index(
                    idx_format.format(tbl_name=cls.__tablename__,
                                      col_name=key), key))
        indices.append({"schema": "cve"})
        return tuple(indices)


class CweBase(BaseModel):
    __table_args__ = {"schema": "cwe"}
    __abstract__ = True
