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

from sqlalchemy import or_, and_
from flask import jsonify, make_response, Blueprint, abort

from app.auth.acls import skip_authorization
from data.database import DEFAULT_DATABASE as db
from data.models import Vulnerability, Nvd, Description, Cpe

bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


@bp.errorhandler(403)
def api_403(ex=None):
    """Return a 403 in JSON format."""
    del ex
    return make_response(jsonify({"error": "Forbidden", "code": 403}), 403)


@bp.errorhandler(404)
def api_404(ex=None):
    """Return a 404 in JSON format."""
    del ex
    return make_response(jsonify({"error": "Not found", "code": 404}), 404)


@bp.errorhandler(500)
def api_500(ex=None):
    """Return a 500 in JSON format."""
    del ex
    return make_response(jsonify({"error": "Internal server error", "code": 500}), 500)


@bp.route("/product/<vendor_id>/<product_id>")
@skip_authorization
def vulns_by_product(vendor_id=None, product_id=None):
    """View vulns associated to product."""
    if product_id is None or product_id is None:
        return abort(404)
    nvd_ids = (
        db.session.query(Cpe.nvd_json_id)
        .filter(and_(Cpe.vendor == vendor_id, Cpe.product == product_id))
        .distinct()
        .all()
    )
    count = len(nvd_ids)
    cve = db.session.query(Nvd.cve_id).filter(Nvd.id.in_(nvd_ids)).all()
    return jsonify({"count": count, "cve_ids": [x for x, in cve]})


def _cpes_to_json(products):
    """Jsonify Cpes for API routes."""
    count = len(products)
    return jsonify(
        {
            "count": count,
            "products": [{"product": x, "vendor": y} for x, y, in products],
        }
    )  # yapf: disable


@bp.route("/search/product:<name>")
@skip_authorization
def search_product(name=None):
    """Return list of products matching name."""
    products = (
        db.session.query(Cpe.product, Cpe.vendor)
        .filter(Cpe.product.like(f"%{name}%"))
        .distinct()
        .all()
    )
    return _cpes_to_json(products)


@bp.route("/search/vendor:<name>")
@skip_authorization
def search_vendor(name=None):
    """Return list of vendors matching name."""
    products = (
        db.session.query(Cpe.product, Cpe.vendor)
        .filter(Cpe.vendor.like(f"%{name}%"))
        .distinct()
        .all()
    )
    return _cpes_to_json(products)


@bp.route("/search/vendor_or_product:<name>")
@bp.route("/search/product_or_vendor:<name>")
@skip_authorization
def search_product_or_vendor(name=None):
    """Return list of products and vendor matching name."""
    products = (
        db.session.query(Cpe.product, Cpe.vendor)
        .filter(or_(Cpe.product.like(f"%{name}%"), Cpe.vendor.like(f"%{name}%")))
        .distinct()
        .all()
    )
    return _cpes_to_json(products)


@bp.route("/search/vendor:<vendor>/product:<product>")
@bp.route("/search/product:<product>/vendor:<vendor>")
@skip_authorization
def search_product_vendor(vendor=None, product=None):
    """Return list of products matching product and vendors matching vendor."""
    if product is None or vendor is None:
        return abort(404)
    products = (
        db.session.query(Cpe.product, Cpe.vendor)
        .filter(and_(Cpe.product.like(f"%{product}%"), Cpe.vendor.like(f"%{vendor}%")))
        .distinct()
        .all()
    )
    return _cpes_to_json(products)


@bp.route("/search/description:<description>")
@skip_authorization
def vulns_for_description(description=None):
    """View vulns associated to description."""
    if description is None:
        return abort(404)
    nvd_ids = (
        db.session.query(Description.nvd_json_id)
        .filter(Description.value.like(f"%{description}%"))
        .distinct()
        .all()
    )
    count = len(nvd_ids)
    cve = db.session.query(Nvd.cve_id).filter(Nvd.id.in_(nvd_ids)).all()
    return jsonify({"count": count, "cve_ids": [x for x, in cve]})


@bp.route("/<cve_id>")
@skip_authorization
def vuln_view(cve_id=None):
    if cve_id is None:
        return abort(404)
    vuln = Vulnerability.query.filter_by(cve_id=cve_id).first()
    if vuln is None:
        vuln = Nvd.query.filter_by(cve_id=cve_id).first()
        if vuln is None:
            return abort(404)
    return jsonify(vuln.to_json())


@bp.route("/details/<cve_id>")
@skip_authorization
def vuln_view_detailed(cve_id=None):
    if cve_id is None:
        return abort(404)
    vuln = Vulnerability.query.filter_by(cve_id=cve_id).first()
    if vuln is None:
        vuln = Nvd.query.filter_by(cve_id=cve_id).first()
        if vuln is None:
            return abort(404)
    return jsonify(vuln.to_json_full())
