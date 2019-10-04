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
from app.vulnerability.views.vulncode_db import VulncodeDB
from flask import Blueprint
from flask import render_template
from flask import send_from_directory


bp = Blueprint("frontend", __name__)


@bp.route("/static/<path:path>")
def serve_static(path):
    return send_from_directory("static", path)


@bp.route("/")
def serve_index():
    vcdb = VulncodeDB()
    return render_template("index.html", vcdb=vcdb)


@bp.route("/maintenance")
def maintenance():
    return render_template("maintenance.html")


@bp.route("/list_entries")
def list_entries():
    vcdb = VulncodeDB()
    return render_template("list_vuln_entries.html", vcdb=vcdb)
