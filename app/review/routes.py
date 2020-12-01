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

from flask import Blueprint, render_template, g
from sqlakeyset import get_page  # type: ignore
from sqlakeyset.results import s as sqlakeysetserial  # type: ignore
from sqlalchemy import desc, asc, or_
from bouncer.constants import READ  # type: ignore

from app.auth.acls import requires
from app.vulnerability.views.vulncode_db import VulnViewTypesetPaginationObjectWrapper
from data.models import Vulnerability, Nvd
from data.models.nvd import default_nvd_view_options
from data.models.vulnerability import VulnerabilityState
from data.database import DEFAULT_DATABASE
from lib.utils import parse_pagination_param

bp = Blueprint("review", __name__, url_prefix="/review")
db = DEFAULT_DATABASE


def serialize_enum(val):
    return "s", val.name


def unserialize_enum(val):
    return val


sqlakeysetserial.custom_serializations = {VulnerabilityState: serialize_enum}
sqlakeysetserial.custom_unserializations = {VulnerabilityState: unserialize_enum}


def get_pending_proposals_paged():
    entries = db.session.query(Vulnerability, Nvd)
    entries = entries.filter(Vulnerability.state != VulnerabilityState.PUBLISHED)
    entries = entries.outerjoin(Vulnerability, Nvd.cve_id == Vulnerability.cve_id)
    entries = entries.order_by(asc(Vulnerability.state), desc(Nvd.id))
    bookmarked_page = parse_pagination_param("review_p")
    per_page = 10
    entries_full = entries.options(default_nvd_view_options)
    review_vulns = get_page(entries_full, per_page, page=bookmarked_page)
    review_vulns = VulnViewTypesetPaginationObjectWrapper(review_vulns.paging)
    return review_vulns


def get_reviewed_proposals_paged():
    entries = db.session.query(Vulnerability, Nvd)
    entries = entries.filter(
        or_(
            Vulnerability.state == VulnerabilityState.PUBLISHED,
            Vulnerability.state == VulnerabilityState.REVIEWED,
            Vulnerability.state == VulnerabilityState.ARCHIVED,
        ),
        Vulnerability.reviewer == g.user,
    )
    entries = entries.outerjoin(Vulnerability, Nvd.cve_id == Vulnerability.cve_id)
    entries = entries.order_by(asc(Vulnerability.state), desc(Nvd.id))
    bookmarked_page = parse_pagination_param("reviewed_p")
    per_page = 10
    entries_full = entries.options(default_nvd_view_options)
    review_vulns = get_page(entries_full, per_page, page=bookmarked_page)
    review_vulns = VulnViewTypesetPaginationObjectWrapper(review_vulns.paging)
    return review_vulns


# Create a catch all route for profile identifiers.
@bp.route("/list")
@requires(READ, "Proposal")
def review_list():
    review_vulns = get_pending_proposals_paged()
    reviewed_vulns = get_reviewed_proposals_paged()
    return render_template(
        "review/list.html", review_vulns=review_vulns, reviewed_vulns=reviewed_vulns
    )
