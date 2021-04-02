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
import logging

from itertools import zip_longest
from typing import Dict, Tuple, Any, Union, Optional, List

from flask_marshmallow import Marshmallow  # type: ignore
from flask_sqlalchemy import DefaultMeta  # type: ignore
from flask_sqlalchemy import SQLAlchemy as SQLAlchemyBase
from sqlalchemy import Index, Column, Integer, func, DateTime, inspect
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapper, RelationshipProperty
from sqlalchemy.orm.attributes import History
from sqlalchemy.orm.interfaces import MapperProperty
from sqlalchemy.orm.state import InstanceState, AttributeState

log = logging.getLogger(__name__)


# Adding the "pool_pre_ping" command to avoid mysql server has gone away issues.
# Note: This will slightly degrade performance. It might be better to adjust
#       MariaDB server settings.
class SQLAlchemy(SQLAlchemyBase):
    def apply_pool_defaults(self, app, options):
        options = super().apply_pool_defaults(app, options)
        options["pool_pre_ping"] = True
        return options


db = SQLAlchemy()
ma = Marshmallow()  # pylint: disable=invalid-name

BaseModel: DefaultMeta = db.Model

ChangeUnion = Union[Tuple[Any, Any], Dict[str, Any], List[Any]]
Changes = Dict[str, ChangeUnion]


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

    def model_changes(self, *, already_tested=None) -> Changes:
        """Returns the changed attributes of this instance.

        Returns:
            a dictionary mapping the attributes to (new, old) tuples or a
            recursive version if the attribute is a list or reference.
        """

        def inner(current) -> Optional[Union[List[Any], Changes]]:
            if isinstance(current, list):
                res = [inner(item) for item in current]
                if any(res):
                    return res
            elif hasattr(current, "model_changes"):
                return current.model_changes(already_tested=already_tested)
            return None

        changes: Changes = {}
        if already_tested is None:
            already_tested = {id(self)}
        elif id(self) in already_tested:
            return changes
        already_tested.add(id(self))
        state: InstanceState = inspect(self)
        attr: AttributeState
        for name, attr in state.attrs.items():
            hist: History = attr.load_history()
            if hist.has_changes():
                changes[name] = hist[0], hist[2]
            else:
                subchanges = inner(getattr(self, name))
                if subchanges:
                    changes[name] = subchanges
        return changes

    def diff(self, other: BaseModel, *, already_tested=None) -> Changes:
        """Returns the difference between this instance and the given one.

        Returns:
            a dictionary mapping the attributes to (new, old) tuples or a
            recursive version if the attribute is a list or reference.
        """
        changes: Changes = {}
        if already_tested is None:
            already_tested = {id(self), id(other)}
        elif id(self) in already_tested and id(other) in already_tested:
            return changes
        already_tested.add(id(self))
        already_tested.add(id(other))
        if id(self) == id(other):  # identity cache
            log.warning("Comparing the same instance (%r). Identity cache?", self)
            return self.model_changes()
        clz = type(self)
        oclz = type(other)
        if not isinstance(other, clz):
            raise TypeError(
                "Instance of {} expected. Got {}".format(clz.__name__, oclz.__name__)
            )

        def innerdiff(current, other) -> Optional[ChangeUnion]:
            if current is None and other is None:
                return None
            if current is None or other is None:
                return (current, other)
            if hasattr(current, "diff"):
                return current.diff(other, already_tested=already_tested)
            if isinstance(current, list) and isinstance(other, list):
                res = []
                for cur, oth in zip_longest(current, other):
                    res.append(innerdiff(cur, oth))
                if all(res):
                    return res
            elif current != other:
                return (current, other)
            return None

        mapper: Mapper = inspect(clz)
        name: str
        attr: MapperProperty
        for name, attr in mapper.attrs.items():  # type: ignore
            # log.debug('Compare %s of %s <> %s', name, clz, oclz)
            other_value = getattr(other, name)
            current_value = getattr(self, name)

            if isinstance(attr, RelationshipProperty) and other_value is None:
                for col in attr.local_columns:
                    cname = col.name
                    if innerdiff(getattr(self, cname), getattr(other, cname)):
                        break
                else:
                    continue
                if name in changes:
                    continue
            subchanges = innerdiff(current_value, other_value)
            if subchanges:
                changes[name] = subchanges

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
                Index(idx_format.format(tbl_name=cls.__tablename__, col_name=key), key)
            )
        indices.append({"schema": "cve"})
        return tuple(indices)


class CweBase(BaseModel):
    __table_args__ = {"schema": "cwe"}
    __abstract__ = True
