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
def test_existing_product_with_vulns(client):
    resp = client.get("/product/Vendor 1/Product 1")
    assert b"Vendor 1" in resp.data
    assert b"Product 1" in resp.data
    assert b"No results found" not in resp.data
    assert b"Annotated" in resp.data


@pytest.mark.integration
def test_existing_product_without_vulns(client):
    resp = client.get("/product/Vendor 11/Product 1")
    assert b"Vendor 11" in resp.data
    assert b"Product 1" in resp.data
    assert b"No results found" not in resp.data
    assert b"Annotated" in resp.data


@pytest.mark.integration
def test_non_existing_product(client):
    resp = client.get("/product/Vendor 1/No Product")
    assert b"Vendor 1" in resp.data
    assert b"No Product" in resp.data
    assert b"No results found" in resp.data


@pytest.mark.integration
def test_non_existing_vendor(client):
    resp = client.get("/product/No Vendor/Product 1")
    assert b"No Vendor" in resp.data
    assert b"Product 1" in resp.data
    assert b"No results found" in resp.data
