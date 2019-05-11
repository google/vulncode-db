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

from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from data.utils import populate_models
from data.models.base import MainBase


class User(MainBase):
    email = Column(String(256), unique=True)
    full_name = Column(String(256))
    profile_picture = Column(String(256))
    # TODO: Find a fix to import the relationship below. Otherwise, SQL will
    #  complain when create_all is invoked due to problems resolving foreign keys.
    # vulns = relationship('Vulnerability')
    # vulnerabilities = relationship('Vulnerability', back_populates='creator')

    @property
    def name(self):
        return self.email.split("@", 1)[0]


# must be set after all definitions
__all__ = populate_models(__name__)
