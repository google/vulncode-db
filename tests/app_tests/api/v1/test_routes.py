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

VULN_INFO_VARIANTS = [
    (
        "CVE-1970-1000",
        200,
        {
            "cve_id": "CVE-1970-1000",
            "comment": "Vulnerability 1 comment",
            "description": "Description 1",
        },
    ),
    (
        "CVE-1970-2000",
        200,
        {"cve_id": "CVE-1970-2000", "comment": "", "description": "Description 11"},
    ),
    ("CVE-9999-9999", 404, {}),
    ("", 404, {}),
]

VULN_INFO_DETAILED_VARIANTS = [
    (
        "CVE-1970-1000",
        200,
        {
            "cve_id": "CVE-1970-1000",
            "comment": "Vulnerability 1 comment",
            "description": "Description 1",
            "commits": [
                {
                    "commit_hash": "1234568",
                    "commit_link": "https://github.com/OWNER/REPO1/commit/1234568",
                    "relevant_files": [],
                    "repo_name": "REPO1",
                    "repo_owner": "OWNER",
                    "repo_url": "https://github.com/OWNER/REPO1",
                }
            ],
        },
    ),
    (
        "CVE-1970-2000",
        200,
        {
            "cve_id": "CVE-1970-2000",
            "comment": "",
            "description": "Description 11",
            "commits": [],
        },
    ),
    ("CVE-9999-9999", 404, {}),
    ("", 404, {}),
]

PRDOUCT_SEARCH_VARIANTS = [
    ("Product 1", 200, {"count": 20}),
    ("Product 10", 200, {"count": 0}),
    ("Foo", 200, {"count": 0}),
    ("", 404, {}),
]

VENDOR_SEARCH_VARIANTS = [
    ("Vendor 1", 200, {"count": 33}),
    ("Vendor 10", 200, {"count": 3}),
    ("Foo", 200, {"count": 0}),
    ("", 404, {}),
]

VENDOR_AND_PRODUCT_SEARCH_VARIANTS = [
    ("Vendor 1", "Product 1", 200, {"count": 11}),
    ("Vendor 1", "Product 10", 200, {"count": 0}),
    ("Vendor 1", "", 404, {}),
    ("Vendor 10", "Product 1", 200, {"count": 1}),
    ("Vendor 10", "Product 10", 200, {"count": 0}),
    ("Vendor 10", "", 404, {}),
    ("Foo", "Product 1", 200, {"count": 0}),
    ("Foo", "Product 10", 200, {"count": 0}),
    ("Foo", "", 404, {}),
    ("", "Product 1", 404, {}),
    ("", "Product 10", 404, {}),
    ("", "", 404, {}),
]

VENDOR_OR_PRODUCT_SEARCH_VARIANTS = PRDOUCT_SEARCH_VARIANTS + VENDOR_SEARCH_VARIANTS

DESCRIPTION_SEARCH_VARIANTS = [
    (
        "Description 1",
        200,
        {
            "count": 11,
            "cve_ids": ["CVE-1970-1000", "CVE-1970-1009"]
            + [f"CVE-1970-{i}" for i in range(2000, 2009)],
        },
    ),
    ("Description", 200, {"count": 20}),
    ("Foo", 200, {"count": 0}),
    ("", 404, {}),
]

VENDOR_AND_PRODUCT_VARIANTS = [
    ("Vendor 1", "Product 1", 200, {"count": 1}),
    ("Vendor 1", "Product 10", 200, {"count": 0}),
    ("Vendor 1", "", 404, {}),
    ("Vendor 10", "Product 1", 200, {"count": 1}),
    ("Vendor 10", "Product 10", 200, {"count": 0}),
    ("Vendor 10", "", 404, {}),
    ("Foo", "Product 1", 200, {"count": 0}),
    ("Foo", "Product 10", 200, {"count": 0}),
    ("Foo", "", 404, {}),
    ("", "Product 1", 404, {}),
    ("", "Product 10", 404, {}),
    ("", "", 404, {}),
]


@pytest.mark.integration
@pytest.mark.parametrize(
    "cve_id, expected_code, expected_attributes", VULN_INFO_VARIANTS
)
def test_get_vulnerability_info_by_cve(
    client, cve_id, expected_code, expected_attributes
):
    resp = client.get(f"/api/v1/{cve_id}")

    assert resp.headers.get("Content-Type") == "application/json"
    assert resp.status_code == expected_code
    for k, v in expected_attributes.items():
        assert resp.json[k] == v


@pytest.mark.integration
@pytest.mark.parametrize(
    "cve_id, expected_code, expected_attributes", VULN_INFO_DETAILED_VARIANTS
)
def test_get_vulnerability_info_details_by_cve(
    client, cve_id, expected_code, expected_attributes
):
    resp = client.get(f"/api/v1/details/{cve_id}")

    assert resp.headers.get("Content-Type") == "application/json"
    assert resp.status_code == expected_code
    for k, v in expected_attributes.items():
        assert resp.json[k] == v


@pytest.mark.integration
@pytest.mark.parametrize(
    "product, expected_code, expected_attributes", PRDOUCT_SEARCH_VARIANTS
)
def test_search_by_product(client, product, expected_code, expected_attributes):
    resp = client.get(f"/api/v1/search/product:{product}")

    assert resp.headers.get("Content-Type") == "application/json"
    assert resp.status_code == expected_code
    for k, v in expected_attributes.items():
        assert resp.json[k] == v


@pytest.mark.integration
@pytest.mark.parametrize(
    "vendor, expected_code, expected_attributes", VENDOR_SEARCH_VARIANTS
)
def test_search_by_vendor(client, vendor, expected_code, expected_attributes):
    resp = client.get(f"/api/v1/search/vendor:{vendor}")

    assert resp.headers.get("Content-Type") == "application/json"
    assert resp.status_code == expected_code
    for k, v in expected_attributes.items():
        assert resp.json[k] == v


@pytest.mark.integration
@pytest.mark.parametrize(
    "vendor, product, expected_code, expected_attributes",
    VENDOR_AND_PRODUCT_SEARCH_VARIANTS,
)
def test_search_by_vendor_and_product(
    client, vendor, product, expected_code, expected_attributes
):
    resp = client.get(f"/api/v1/search/vendor:{vendor}/product:{product}")

    assert resp.headers.get("Content-Type") == "application/json"
    assert resp.status_code == expected_code
    for k, v in expected_attributes.items():
        assert resp.json[k] == v


@pytest.mark.integration
@pytest.mark.parametrize(
    "vendor_product, expected_code, expected_attributes",
    VENDOR_OR_PRODUCT_SEARCH_VARIANTS,
)
def test_search_by_vendor_or_product(
    client, vendor_product, expected_code, expected_attributes
):
    resp = client.get(f"/api/v1/search/vendor_or_product:{vendor_product}")

    assert resp.headers.get("Content-Type") == "application/json"
    assert resp.status_code == expected_code
    for k, v in expected_attributes.items():
        assert resp.json[k] == v

    resp = client.get(f"/api/v1/search/product_or_vendor:{vendor_product}")

    assert resp.headers.get("Content-Type") == "application/json"
    assert resp.status_code == expected_code
    for k, v in expected_attributes.items():
        assert resp.json[k] == v


@pytest.mark.integration
@pytest.mark.parametrize(
    "description, expected_code, expected_attributes", DESCRIPTION_SEARCH_VARIANTS
)
def test_search_by_description(client, description, expected_code, expected_attributes):
    resp = client.get(f"/api/v1/search/description:{description}")

    assert resp.headers.get("Content-Type") == "application/json"
    assert resp.status_code == expected_code
    for k, v in expected_attributes.items():
        assert resp.json[k] == v


@pytest.mark.integration
@pytest.mark.parametrize(
    "vendor, product, expected_code, expected_attributes", VENDOR_AND_PRODUCT_VARIANTS
)
def test_get_by_vendor_and_product(
    client, vendor, product, expected_code, expected_attributes
):
    resp = client.get(f"/api/v1/product/{vendor}/{product}")

    assert resp.headers.get("Content-Type") == "application/json"
    assert resp.status_code == expected_code
    for k, v in expected_attributes.items():
        assert resp.json[k] == v
