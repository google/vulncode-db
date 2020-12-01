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
from data.utils import populate_models


def test_populate_models_returns_empty_array_on_unknown_module():
    assert populate_models("this_module_does_not_exist") == []


def test_populate_models_returns_empty_array_on_invalid_modules():
    assert populate_models("sys") == []
    assert populate_models("lib") == []
    assert populate_models("data") == []


def test_populate_models_returns_models():
    models = populate_models("data.models")
    assert len(models) > 0
    assert "Vulnerability" in models
    assert "Nvd" in models
