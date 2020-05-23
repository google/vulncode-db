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

from flask import (Blueprint, render_template, g)
from sqlakeyset import get_page
from sqlalchemy import desc

from app.auth.routes import admin_required
from app.vulnerability.views.vulncode_db import (
    VulnViewTypesetPaginationObjectWrapper, )

from app import flash_error
from data.models import Vulnerability, Nvd
from data.models.nvd import default_nvd_view_options
from data.models.vulnerability import VulnerabilityState
from data.database import DEFAULT_DATABASE
from lib.utils import parse_pagination_param

bp = Blueprint("review", __name__, url_prefix="/review")
db = DEFAULT_DATABASE


# Create a catch all route for profile identifiers.
@bp.route("/list")
@admin_required()
def list(vendor: str = None, profile: str = None):
    entries = db.session.query(Vulnerability, Nvd)
    entries = entries.filter(
        Vulnerability.state != VulnerabilityState.PUBLISHED)
    entries = entries.outerjoin(Vulnerability,
                                Nvd.cve_id == Vulnerability.cve_id)
    entries = entries.order_by(desc(Nvd.id))

    bookmarked_page = parse_pagination_param("review_p")
    per_page = 10
    entries_full = entries.options(default_nvd_view_options)
    review_vulns = get_page(entries_full, per_page, page=bookmarked_page)
    review_vulns = VulnViewTypesetPaginationObjectWrapper(review_vulns.paging)
    return render_template("review/review_list.html",
                           review_vulns=review_vulns)
