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
import enum

from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from data.utils import populate_models
from data.models.base import MainBase, BaseModel


class PredefinedRoles(enum.Enum):
    USER = enum.auto()
    REVIEWER = enum.auto()
    ADMIN = enum.auto()

    def __str__(self):
        return self.name


class UserRole(BaseModel):
    role_id = Column(Integer,
                     ForeignKey('role.id'),
                     nullable=False,
                     primary_key=True)
    user_id = Column(Integer,
                     ForeignKey('user.id'),
                     nullable=False,
                     primary_key=True)


class Role(MainBase):
    name = Column(String(256), nullable=False, unique=True)
    users = relationship('User', secondary='user_role', back_populates='roles')

    def __str__(self):
        return self.name


class User(MainBase):
    email = Column(String(256), unique=True, nullable=False)
    full_name = Column(String(256), nullable=True)
    profile_picture = Column(String(256), nullable=True)
    roles = relationship(Role, secondary='user_role', back_populates='users')

    @property
    def name(self):
        return self.email.split("@", 1)[0]

    def to_json(self):
        """Serialize object properties as dict."""
        # TODO: Refactor how we will surface this.
        return {'username': 'anonymous'}

    def _has_role(self, role):
        for r in self.roles:
            if r.name == str(role):
                return True
        return False

    def is_admin(self):
        return self._has_role(PredefinedRoles.ADMIN)

    def is_reviewer(self):
        return self._has_role(PredefinedRoles.REVIEWER)


# must be set after all definitions
__all__ = populate_models(__name__)
