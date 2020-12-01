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

from flask import Blueprint, render_template, jsonify
from sqlakeyset import get_page  # type: ignore
from sqlalchemy import and_, desc
from sqlalchemy.orm import joinedload, Load

from app.auth.acls import skip_authorization
from app.vulnerability.views.vulncode_db import (
    VulnViewTypesetPaginationObjectWrapper,
)
from data.models.nvd import default_nvd_view_options, Cpe, Nvd
from data.models.vulnerability import Vulnerability
from data.database import DEFAULT_DATABASE
from lib.utils import parse_pagination_param

bp = Blueprint("product", __name__, url_prefix="/product")
db = DEFAULT_DATABASE


def get_unique_repo_urls(vulnerability_entries):
    """
    Retrieves a unique list of repository urls sorted by frequency.
    :param vulnerability_entries:
    :return:
    """
    unique_repo_urls = {}
    for entry in vulnerability_entries:
        if entry.Vulnerability is None:
            continue
        commits = entry.Vulnerability.commits
        for commit in commits:
            repo_url = commit.repo_url
            if repo_url not in unique_repo_urls:
                unique_repo_urls[repo_url] = 0
            unique_repo_urls[repo_url] += 1

    sorted_urls = sorted(
        unique_repo_urls.items(), key=lambda item: item[1], reverse=True
    )
    repo_urls = [pair[0] for pair in sorted_urls]
    return repo_urls


def get_entries_commits(full_base_query):
    """
    Takes a base query and only selects commit relevant data.
    :param full_base_query:
    :return:
    """
    # pylint: disable=no-member
    entries_commits = full_base_query.options(Load(Vulnerability).defer("*"))
    entries_commits = entries_commits.options(Load(Nvd).defer("*"))
    # pylint: enable=no-member
    entries_commits = entries_commits.options(joinedload(Vulnerability.commits))
    entries_subset = entries_commits.all()
    return entries_subset


# Create a catch all route for product identifiers.
@bp.route("/<vendor>/<product>")
@skip_authorization
def product_view(vendor: str = None, product: str = None):
    sub_query = (
        db.session.query(Cpe.nvd_json_id)
        .filter(and_(Cpe.vendor == vendor, Cpe.product == product))
        .distinct()
    )
    number_vulns = sub_query.count()

    entries = db.session.query(Vulnerability, Nvd)
    entries = entries.filter(Nvd.id.in_(sub_query)).with_labels()
    entries = entries.outerjoin(Vulnerability, Nvd.cve_id == Vulnerability.cve_id)
    entries = entries.order_by(desc(Nvd.id))

    bookmarked_page = parse_pagination_param("product_p")

    per_page = 10
    entries_full = entries.options(default_nvd_view_options)
    product_vulns = get_page(entries_full, per_page, page=bookmarked_page)
    product_vulns = VulnViewTypesetPaginationObjectWrapper(product_vulns.paging)

    entries_commits = get_entries_commits(entries)
    repo_urls = get_unique_repo_urls(entries_commits)

    return render_template(
        "product/view.html",
        vendor=vendor,
        product=product,
        product_vulns=product_vulns,
        repo_urls=repo_urls,
        number_vulns=number_vulns,
    )


# Used for autocomplete forms supports filtering.
@bp.route("/list:<filter_term>")
@skip_authorization
def list_all(filter_term: str = None):
    if not filter_term or len(filter_term) < 3:
        return "{}"
    # Only search the product name for now.
    products = (
        db.session.query(Cpe.product, Cpe.vendor)
        .filter(Cpe.product.like(f"%{filter_term}%"))
        .distinct()
        .all()
    )
    return jsonify(products)
