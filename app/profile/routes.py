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

from flask import (Blueprint, render_template, g, abort, flash, request)
from sqlakeyset import get_page
from sqlalchemy import desc
from bouncer.constants import READ, EDIT

from app.auth.acls import skip_authorization, requires, ensure
from app.exceptions import InvalidIdentifierException
from app.vulnerability.views.details import VulnerabilityDetails
from app.vulnerability.views.vulncode_db import (
    VulnViewTypesetPaginationObjectWrapper, )

from app import flash_error
from data.forms import VulnerabilityDetailsForm, UserProfileForm
from data.models import Vulnerability, Nvd, User
from data.models.nvd import default_nvd_view_options
from data.models.vulnerability import VulnerabilityState
from data.database import DEFAULT_DATABASE
from lib.utils import parse_pagination_param

bp = Blueprint("profile", __name__, url_prefix="/profile")
db = DEFAULT_DATABASE


def _get_vulnerability_details(vcdb_id, vuln_id=None,
                               simplify_id: bool = True):
    try:
        vulnerability_details = VulnerabilityDetails(vcdb_id, vuln_id)
        if simplify_id:
            vulnerability_details.validate_and_simplify_id()
        # Drop everything else.
        if not vulnerability_details.vulnerability_view:
            abort(404)
        return vulnerability_details
    except InvalidIdentifierException:
        abort(404)


def update_proposal(vuln: Vulnerability, form: VulnerabilityDetailsForm):
    form.populate_obj(vuln)
    vuln.make_reviewable()
    db.session.add(vuln)
    db.session.commit()

    flash(
        "Your proposal is in the review queue. You can monitor progress in your Proposals Section.",
        "success")


# Create a catch all route for profile identifiers.
@bp.route("/proposal/<vuln_id>/edit", methods=["GET", "POST"])
@requires(EDIT, Vulnerability)
def edit_proposal(vuln_id: str = None):
    vulnerability_details = _get_vulnerability_details(None,
                                                       vuln_id,
                                                       simplify_id=False)
    view = vulnerability_details.vulnerability_view
    vuln = vulnerability_details.get_or_create_vulnerability()
    form = VulnerabilityDetailsForm(obj=vuln)

    # Populate the form data from the vulnerability view if necessary.
    if form.comment.data == "":
        form.comment.data = view.comment

    if request.method == 'POST' and not form.validate():
        flash_error("Your proposal contains invalid data, please correct.")

    form_submitted = form.validate_on_submit()
    if form_submitted and view.is_creator():
        update_proposal(vuln, form)

    return render_template("profile/edit_proposal.html",
                           vulnerability_details=vulnerability_details,
                           form=form)


# Create a catch all route for profile identifiers.
@bp.route("/proposals")
@requires('READ_OWN', 'Proposal')
def view_proposals(vendor: str = None, profile: str = None):
    entries = db.session.query(Vulnerability, Nvd)
    entries = entries.filter(Vulnerability.creator == g.user)
    entries = entries.outerjoin(Vulnerability,
                                Nvd.cve_id == Vulnerability.cve_id)
    entries = entries.order_by(desc(Nvd.id))

    bookmarked_page = parse_pagination_param("proposal_p")
    per_page = 10
    entries_non_processed = entries.filter(~Vulnerability.state.in_(
        [VulnerabilityState.ARCHIVED, VulnerabilityState.PUBLISHED]))
    entries_full = entries_non_processed.options(default_nvd_view_options)
    proposal_vulns = get_page(entries_full, per_page, page=bookmarked_page)
    proposal_vulns = VulnViewTypesetPaginationObjectWrapper(
        proposal_vulns.paging)

    entries_processed = entries.filter(
        Vulnerability.state.in_(
            [VulnerabilityState.ARCHIVED, VulnerabilityState.PUBLISHED]))
    bookmarked_page_processed = parse_pagination_param("proposal_processed_p")
    entries_processed_full = entries_processed.options(
        default_nvd_view_options)
    proposal_vulns_processed = get_page(entries_processed_full,
                                        per_page,
                                        page=bookmarked_page_processed)
    proposal_vulns_processed = VulnViewTypesetPaginationObjectWrapper(
        proposal_vulns_processed.paging)

    return render_template(
        "profile/proposals_view.html",
        proposal_vulns=proposal_vulns,
        proposal_vulns_processed=proposal_vulns_processed,
    )


import flask_wtf.csrf


@bp.route("/", methods=["GET", "POST"])
@bp.route("/<int:user_id>", methods=["GET", "POST"])
def index(user_id=None):
    if user_id is None:
        user = g.user
    else:
        user: User = User.query.get_or_404(user_id)
    if request.method == "GET":
        ensure(READ, user)
    else:
        ensure(EDIT, user)
    form = UserProfileForm(obj=user)
    if form.validate_on_submit():
        form.populate_obj(user)
        db.session.add(user)
        db.session.commit()
    return render_template("profile/index.html", form=form, user=user)
