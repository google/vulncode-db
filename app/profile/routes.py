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

import re
from flask import (Blueprint, render_template)
from sqlakeyset import get_page  # type: ignore
from sqlalchemy import and_, desc
from sqlalchemy.orm import joinedload, Load

from app.vulnerability.views.vulncode_db import VulnViewTypesetPaginationObjectWrapper
from data.models.nvd import default_nvd_view_options, Cpe, Nvd
from data.models.vulnerability import Vulnerability
from data.database import DEFAULT_DATABASE
from lib.utils import parse_pagination_param

bp = Blueprint("profile", __name__, url_prefix="/profile")
db = DEFAULT_DATABASE


# Create a catch all route for profile identifiers.
@bp.route("/proposals")
def view_proposals(vendor: str = None, profile: str = None):
    return render_template("profile/proposals_view.html")
