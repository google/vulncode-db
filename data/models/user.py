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
import re
import uuid

from sqlalchemy import Column, String, Integer, ForeignKey, Enum, Boolean, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import null
from sqlalchemy.sql.schema import PrimaryKeyConstraint

from data.utils import populate_models
from data.models.base import MainBase, BaseModel
from lib.statemachine import StateMachine, transition


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


class InviteCode(MainBase):
    code = Column(String(36),
                  unique=True,
                  nullable=False,
                  index=True,
                  default=lambda: str(uuid.uuid4()))
    remaining_uses = Column(Integer, nullable=False, default=1)
    description = Column(String(255), nullable=False)
    roles = relationship(Role, secondary='invite_role')
    users = relationship('User', back_populates='invite_code')


invite_roles = Table(
    'invite_role', BaseModel.metadata,
    Column('invite_id', ForeignKey(InviteCode.id), nullable=False),
    Column('role_id', ForeignKey(Role.id), nullable=False),
    PrimaryKeyConstraint('invite_id', 'role_id'))


class UserState(StateMachine):
    REGISTERED = 0
    ACTIVE = 1
    BLOCKED = 2

    enable = transition(REGISTERED, ACTIVE)()
    disable = transition(ACTIVE, BLOCKED)()


class User(MainBase):
    email = Column(String(256), unique=True, nullable=False)
    full_name = Column(String(256), nullable=True)
    profile_picture = Column(String(256), nullable=True)
    roles = relationship(Role, secondary='user_role', back_populates='users')
    state = Column(Enum(UserState),
                   default=UserState.REGISTERED,
                   nullable=False)
    hide_name = Column(Boolean, nullable=False, default=True)
    hide_picture = Column(Boolean, nullable=False, default=True)
    invite_code_id = Column(Integer, ForeignKey(InviteCode.id), nullable=True)
    invite_code = relationship(InviteCode, back_populates='users')

    @property
    def name(self):
        if self.hide_name:
            return f'User {self.id}'
        elif self.full_name:
            return self.full_name
        return self.email.split("@", 1)[0]

    @property
    def avatar(self):
        if self.hide_picture or not self.profile_picture:
            return ''
        return self.profile_picture

    def profile_picture_resized(self, px):
        pic = None
        if self.profile_picture:
            pic = self._resize(self.profile_picture, px)
        return pic

    def avatar_resized(self, px):
        return self._resize(self.avatar, px)

    def _resize(self, pic, px):
        if 'googleusercontent.com' in pic:
            pic = re.sub(r'/photo', f'/s{px}-cc-rw/photo', pic)
            pic = re.sub(r'([=/])s\d+-', f'\\1s{px}-', pic)
        return pic

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

    def is_enabled(self):
        return self.state == UserState.ACTIVE

    def is_blocked(self):
        return self.state == UserState.BLOCKED

    def block(self):
        self.state.next_state(UserState.BLOCKED)

    def enable(self):
        if self.state is None:
            self.state = UserState.ACTIVE
        else:
            self.state = self.state.next_state(UserState.ACTIVE)


# must be set after all definitions
__all__ = populate_models(__name__)
