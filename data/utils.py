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

import sys
import inspect

from data.models.base import db, ma


def populate_models(modname):
    mod = sys.modules.get(modname)
    names = []
    if not mod:
        return names

    for name, clazz in inspect.getmembers(mod, inspect.isclass):
        # getattr can't be used here as it also looks into superclasses
        is_abstract = clazz.__dict__.get("__abstract__", False)
        if issubclass(clazz, (db.Model, ma.SQLAlchemyAutoSchema)) and not is_abstract:
            names.append(name)
    return names
