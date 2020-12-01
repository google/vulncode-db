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
from tests.conftest import as_admin
from tests.conftest import as_user
from tests.conftest import set_user

SAVE_VARIANTS = [
    ({}, {}, 400, {"msg": "Please provide a valid CVE ID or Git commit link."}),
    ({"id": "CVE-1970-3000"}, {}, 404, {"msg": "Please create an entry first"}),
    ({"id": "CVE-1970-2000"}, {}, 404, {"msg": "Entry has no linked Git link!"}),
    ({"id": "CVE-1970-1000"}, {}, 200, {"msg": "Update successful."}),
    (
        {"id": "CVE-1970-1000"},
        [
            {
                "path": "/etc/passwd",
                "hash": "12345678",
                "name": "passwd",
                "comments": [
                    {
                        "row_from": 1,
                        "row_to": 10,
                        "text": "a comment",
                        "sort_pos": 0,
                    }
                ],
                "markers": [
                    {
                        "row_from": 1,
                        "row_to": 10,
                        "column_from": 1,
                        "column_to": 10,
                        "class": "vulnerableMarker",
                    }
                ],
            },
        ],
        200,
        {"msg": "Update successful."},
    ),
]


@pytest.mark.integration
@pytest.mark.parametrize("query, data, expected_code, expected_response", SAVE_VARIANTS)
def test_save_editor_data(client, query, data, expected_code, expected_response):
    resp = client.post("/api/save_editor_data", json=data, query_string=query)

    assert resp.status_code == 403
    assert "application/json" in resp.headers["Content-Type"]
    assert b"Forbidden" in resp.data


@pytest.mark.integration
@pytest.mark.parametrize("query, data, expected_code, expected_response", SAVE_VARIANTS)
def test_save_editor_data_as_admin(
    app, client, query, data, expected_code, expected_response
):
    as_admin(client)
    resp = client.post("/api/save_editor_data", json=data, query_string=query)

    assert resp.status_code == expected_code
    assert "application/json" in resp.headers["Content-Type"]
    assert resp.json == expected_response


@pytest.mark.integration
@pytest.mark.parametrize("query, data, expected_code, expected_response", SAVE_VARIANTS)
def test_save_editor_data_as_user(
    app, client, query, data, expected_code, expected_response
):
    with set_user(app, as_user(client)):
        resp = client.post("/api/save_editor_data", json=data, query_string=query)

        assert resp.status_code == 403
        assert "application/json" in resp.headers["Content-Type"]
        assert b"Forbidden" in resp.data
