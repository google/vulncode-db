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
import logging

from bouncer.constants import READ, EDIT, DELETE  # type: ignore
from flask import (
    Blueprint,
    render_template,
    g,
    abort,
    flash,
    request,
    redirect,
    url_for,
)
from sqlakeyset import get_page  # type: ignore
from sqlalchemy import desc

from app.auth.acls import requires, ensure
from app.exceptions import InvalidProducts
from app.vulnerability.views.vulncode_db import VulnViewTypesetPaginationObjectWrapper

from app import flash_error
from data.database import DEFAULT_DATABASE as db
from data.forms import VulnerabilityDetailsForm, UserProfileForm
from data.models import Vulnerability, Nvd, User
from data.models.nvd import default_nvd_view_options
from data.models.vulnerability import VulnerabilityState
from lib.utils import (
    parse_pagination_param,
    update_products,
    get_vulnerability_details,
    clean_vulnerability_changes,
)

bp = Blueprint("profile", __name__, url_prefix="/profile")
log = logging.getLogger(__name__)


def update_proposal(vuln: Vulnerability, form: VulnerabilityDetailsForm):
    form.populate_obj(vuln)

    try:
        new_products = update_products(vuln)
    except InvalidProducts as ex:
        flash_error(ex.args[0])
        return None

    with db.session.no_autoflush:
        changes = vuln.model_changes()
    # ignore metadata
    clean_vulnerability_changes(changes)
    if not changes:
        flash_error(
            "No changes detected. " "Please modify the entry first to propose a change"
        )
        return None
    log.debug("Detected changes: %r", changes)

    vuln.make_reviewable()
    db.session.add(vuln)
    db.session.commit()

    flash(
        "Your proposal is in the review queue. "
        "You can monitor progress in your Proposals Section.",
        "success",
    )
    return new_products


# Create a catch all route for profile identifiers.
@bp.route("/proposal/<vuln_id>/edit", methods=["GET", "POST"])
@requires(EDIT, Vulnerability)
def edit_proposal(vuln_id: str = None):
    vulnerability_details = get_vulnerability_details(None, vuln_id, simplify_id=False)
    view = vulnerability_details.vulnerability_view
    vuln = vulnerability_details.get_or_create_vulnerability()
    ensure(EDIT, vuln)
    form = VulnerabilityDetailsForm(obj=vuln)

    # Populate the form data from the vulnerability view if necessary.
    if form.comment.data == "":
        form.comment.data = view.comment

    if request.method == "POST" and not form.validate():
        flash_error("Your proposal contains invalid data, please correct.")

    form_submitted = form.validate_on_submit()
    if form_submitted and view.is_creator():
        new_products = update_proposal(vuln, form)
        if new_products is not None:
            view.products = [(p.vendor, p.product) for p in new_products]

    return render_template(
        "profile/edit_proposal.html",
        vulnerability_details=vulnerability_details,
        form=form,
    )


# Create a catch all route for profile identifiers.
@bp.route("/proposals")
@requires("READ_OWN", "Proposal")
def view_proposals():
    entries = db.session.query(Vulnerability, Nvd)
    entries = entries.filter(Vulnerability.creator == g.user)
    entries = entries.outerjoin(Vulnerability, Nvd.cve_id == Vulnerability.cve_id)
    entries = entries.order_by(desc(Nvd.id))

    bookmarked_page = parse_pagination_param("proposal_p")
    per_page = 10
    entries_non_processed = entries.filter(
        ~Vulnerability.state.in_(
            [VulnerabilityState.ARCHIVED, VulnerabilityState.PUBLISHED]
        )
    )
    entries_full = entries_non_processed.options(default_nvd_view_options)
    proposal_vulns = get_page(entries_full, per_page, page=bookmarked_page)
    proposal_vulns = VulnViewTypesetPaginationObjectWrapper(proposal_vulns.paging)

    entries_processed = entries.filter(
        Vulnerability.state.in_(
            [VulnerabilityState.ARCHIVED, VulnerabilityState.PUBLISHED]
        )
    )
    bookmarked_page_processed = parse_pagination_param("proposal_processed_p")
    entries_processed_full = entries_processed.options(default_nvd_view_options)
    proposal_vulns_processed = get_page(
        entries_processed_full, per_page, page=bookmarked_page_processed
    )
    proposal_vulns_processed = VulnViewTypesetPaginationObjectWrapper(
        proposal_vulns_processed.paging
    )

    return render_template(
        "profile/proposals_view.html",
        proposal_vulns=proposal_vulns,
        proposal_vulns_processed=proposal_vulns_processed,
    )


@bp.route("/<int:user_id>", methods=["GET"])
def user_profile(user_id=None):
    user: User = User.query.get_or_404(user_id)
    ensure(READ, user)

    vulns = Vulnerability.query.filter(
        Vulnerability.creator == user,
        Vulnerability.state.in_(
            [VulnerabilityState.PUBLISHED, VulnerabilityState.ARCHIVED]
        ),
    ).all()
    return render_template("profile/profile_viewer.html", user=user, vulns=vulns)


@bp.route("/", methods=["GET", "POST"])
def index():
    user = g.user
    if request.method == "GET":
        ensure(READ, user)
    else:
        ensure(EDIT, user)
    form = UserProfileForm(obj=user)
    if form.validate_on_submit():
        form.populate_obj(user)
        db.session.add(user)
        db.session.commit()
    vulns = Vulnerability.query.filter(
        Vulnerability.creator == user,
        Vulnerability.state.in_(
            [VulnerabilityState.PUBLISHED, VulnerabilityState.ARCHIVED]
        ),
    ).all()
    return render_template("profile/index.html", form=form, user=user, vulns=vulns)


@bp.route("/proposal/<vuln_id>/delete", methods=["GET", "POST"])
@requires(DELETE, Vulnerability)
def delete_proposal(vuln_id: str = None):
    vulnerability_details = get_vulnerability_details(None, vuln_id, simplify_id=False)
    vuln = vulnerability_details.get_vulnerability()
    if not vuln:
        abort(404)

    if vuln.state == VulnerabilityState.PUBLISHED:
        flash_error("Can't delete a published entry w/o reverting it first")
        return redirect(url_for("profile.view_proposals"))

    if vuln.state == VulnerabilityState.ARCHIVED:
        flash_error("Can't delete an archived")
        return redirect(url_for("profile.view_proposals"))

    ensure(DELETE, vuln)

    if (
        request.method != "GET"
        and request.form.get("confirm", "false").lower() == "true"
    ):
        db.session.delete(vuln)
        db.session.commit()
        flash("Entry deleted", "success")
        return redirect(url_for("profile.view_proposals"))
    return render_template(
        "vulnerability/delete.html", vuln_view=vulnerability_details.vulnerability_view
    )
