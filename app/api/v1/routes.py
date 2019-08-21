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
from flask import jsonify, make_response, Blueprint

from data.database import DEFAULT_DATABASE as db
from data.models import Vulnerability, Nvd, Description, Cpe

bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


def api_404():
    """Return a 404 in JSON format."""
    return make_response(jsonify({'error': 'Not found', 'code': 404}), 404)


def api_500():
    """Return a 500 in JSON format."""
    return make_response(
        jsonify({
            'error': 'Internal server error',
            'code': 500
        }), 500)


@bp.route("/product/<vendor_id>/<product_id>")
def vulns_by_product(vendor_id=None, product_id=None):
    """View vulns associated to product."""
    if product_id is None or product_id is None:
        return api_404()
    nvd_ids = db.session.query(Cpe.nvd_json_id).filter(
        and_(Cpe.vendor == vendor_id,
             Cpe.product == product_id)).distinct().all()
    count = len(nvd_ids)
    cve = db.session.query(Nvd.cve_id).filter(Nvd.id.in_(nvd_ids)).all()
    return jsonify({"count": count, "cve_ids": [x for x, in cve]})


@bp.route("/search/product/<name>")
def products(name=None):
    """Return list of products matching name."""
    products = db.session.query(Cpe.product, Cpe.vendor).filter(
        or_(Cpe.product.like(f"%{name}%"),
            Cpe.vendor.like(f"%{name}%"))).distinct().all()
    count = len(products)
    return jsonify({
        "count":
        count,
        "products": [{
            'product': x,
            'vendor': y
        } for x, y, in products]
    })


@bp.route("/search/description/<description>")
def vulns_for_description(description=None):
    """View vulns associated to description."""
    if description is None:
        return api_404()
    nvd_ids = db.session.query(Description.nvd_json_id).filter(
        Description.value.like(f'%{description}%')).distinct().all()
    count = len(nvd_ids)
    cve = db.session.query(Nvd.cve_id).filter(Nvd.id.in_(nvd_ids)).all()
    return jsonify({"count": count, "cve_ids": [x for x, in cve]})


@bp.route("/<cve_id>")
def vuln_view(cve_id=None):
    if cve_id is None:
        return api_404()
    vuln = Vulnerability.query.filter_by(cve_id=cve_id).first()
    if vuln is None:
        vuln = Nvd.query.filter_by(cve_id=cve_id).first()
        if vuln is None:
            return api_404()
    return jsonify(vuln.toJson())


@bp.route("/details/<cve_id>")
def vuln_view_detailled(cve_id=None):
    if cve_id is None:
        return api_404()
    vuln = Vulnerability.query.filter_by(cve_id=cve_id).first()
    if vuln is None:
        vuln = Nvd.query.filter_by(cve_id=cve_id).first()
        if vuln is None:
            return api_404()
    return jsonify(vuln.toJsonFull())
