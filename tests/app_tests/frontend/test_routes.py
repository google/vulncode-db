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
import pytest


@pytest.mark.integration
@pytest.mark.production
def test_index(client):
    resp = client.get("/")
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.production
def test_list_entries(client):
    resp = client.get("/list_entries")
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.production
def test_maintenance(client):
    resp = client.get("/maintenance")
    assert resp.status_code == 200
    assert b"Under maintenance" in resp.data


@pytest.mark.integration
@pytest.mark.production
def test_static(client):
    resp = client.get("/static/js/main.js")
    assert resp.status_code == 200
    assert b"Copyright 2019 Google LLC" in resp.data


@pytest.mark.integration
@pytest.mark.production
def test_static_not_found(client):
    resp = client.get("/static/js/foo.bar")
    assert resp.status_code == 404


@pytest.mark.integration
@pytest.mark.production
def test_static_path_traversal(client):
    path = "../" * 100
    resp = client.get("/static/" + path + "etc/passwd")
    assert resp.status_code == 404
