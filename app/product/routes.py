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

from flask import (
    Blueprint,
    render_template,
)
from sqlalchemy import and_

from app.vulnerability.views.vulncode_db import VulnViewSqlalchemyPaginationObjectWrapper
from app.vulnerability.views.vulnerability import VulnerabilityView
from data.models.nvd import default_nvd_view_options, Cpe
from data.database import DEFAULT_DATABASE, Vulnerability, Nvd

bp = Blueprint("product", __name__, url_prefix="/product")
db = DEFAULT_DATABASE

# Create a catch all route for product identifiers.
@bp.route("/<vendor>/<product>")
def product_view(vendor=None, product=None):
    sub_query = db.session.query(Cpe.nvd_json_id).filter(
            and_(Cpe.vendor == vendor, Cpe.product == product)
        ).distinct()

    entries = db.session.query(Vulnerability, Nvd)
    entries = entries.filter(Nvd.id.in_(sub_query)).with_labels()
    entries = entries.outerjoin(Vulnerability, Nvd.cve_id == Vulnerability.cve_id)
    entries = entries.options(default_nvd_view_options)
    #.options(lazyload(Nvd.cpes))
    #entries = entries.order_by(
    #    asc(Vulnerability.date_created), desc(Vulnerability.id))
    product_vulns = entries.paginate(1, per_page=10)
    product_vulns = VulnViewSqlalchemyPaginationObjectWrapper(product_vulns)

    # TODO: Remove this arbitrary limit here and make the queries more efficient.
    entries_subset = entries.limit(50).all()
    repo_urls = []
    for entry in entries_subset:
        if entry.Vulnerability is None or entry.Vulnerability.master_commit is None:
            continue
        vuln_view = VulnerabilityView(
            entry.Vulnerability, entry.Nvd, preview=True)
        commits = [vuln_view.master_commit] + vuln_view.known_commits
        entry_repo_urls = [c.repo_url for c in commits]
        repo_urls += entry_repo_urls
    repo_urls = list(set(repo_urls))

    return render_template(
        "product_view.html",
        vendor=vendor,
        product=product,
        product_vulns=product_vulns,
        repo_urls=repo_urls)
