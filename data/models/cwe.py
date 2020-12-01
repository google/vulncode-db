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

from sqlalchemy import Column, Text, String

from data.models.base import CweBase
from data.utils import populate_models


class CweData(CweBase):
    __tablename__ = "cwe_data"

    cwe_id = Column(String(255), primary_key=True, index=True)
    cwe_name = Column(Text)


# must be set after all definitions
__all__ = populate_models(__name__)
