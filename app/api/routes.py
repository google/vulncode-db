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

from flask import Blueprint, request, current_app, g, make_response, jsonify

from app.auth.acls import admin_required, ensure
from app.exceptions import InvalidIdentifierException
from app.vulnerability.views.details import VulnerabilityDetails

from data.database import DEFAULT_DATABASE as db
from data.models import (
    RepositoryFileComments,
    RepositoryFileMarkers,
    RepositoryFiles,
)
from data.models.vulnerability import ANNOTATE
from lib.utils import create_json_response

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.errorhandler(403)
def api_403(ex=None):
    """Return a 403 in JSON format."""
    del ex
    return make_response(jsonify({"error": "Forbidden", "code": 403}), 403)


@bp.app_errorhandler(404)
def api_404(ex=None):
    """Return a 404 in JSON format."""
    if request.path.startswith(bp.url_prefix):
        return make_response(jsonify({"error": "Not found", "code": 404}), 404)
    return ex


@bp.errorhandler(500)
def api_500(ex=None):
    """Return a 500 in JSON format."""
    del ex
    return make_response(jsonify({"error": "Internal server error", "code": 500}), 500)


def calculate_revision_updates(wrapper, old, new, attrs):
    old_dict = dict(list(zip(list(map(wrapper, old)), old)))
    old_keys = frozenset(list(old_dict.keys()))
    new_dict = dict(list(zip(list(map(wrapper, new)), new)))
    new_keys = frozenset(list(new_dict.keys()))

    intersection = old_keys & new_keys
    current_app.logger.debug(
        f"{len(old_keys)} old, {len(new_keys)} new, "
        f"{len(intersection)} intersecting"
    )

    # archive removed comments
    for k in old_keys - new_keys:
        old = old_dict[k]
        current_app.logger.debug(f"Archiving {k!s}")
        old.archive()

    # filter new comments
    updated_comments = [new_dict[k] for k in new_keys - old_keys]
    for k in intersection:
        old = old_dict[k]
        new = new_dict[k]

        # no changes
        for attr in attrs:
            if getattr(old, attr) != getattr(new, attr):
                break
        else:
            current_app.logger.debug(f"No changes for {k!s}")
            continue
        # archive old version
        current_app.logger.debug(f"Archiving {k!s}")
        old.archive()
        new.revision = old.revision + 1
        updated_comments.append(new)
    return updated_comments


class Hashable:
    def __init__(self, item, key):
        self.item = item
        self.key = key

    @property
    def value(self):
        return self.key(self.item)

    def __eq__(self, other):
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return f"{str(self)} ({hash(self)})"


class HashableComment(Hashable):
    def __init__(self, comment):
        super().__init__(comment, lambda c: (c.row_from, c.row_to))

    def __str__(self):
        return f"comment @ {self.value}"


class HashableMarker(Hashable):
    def __init__(self, marker):
        super().__init__(
            marker, lambda m: (m.row_from, m.row_to, m.column_from, m.column_to)
        )

    def __str__(self):
        msg = "marker @ {0.row_from}:{0.column_from} - {0.row_to}:{0.column_to}"
        return msg.format(self.item)


def update_file_comments(file_obj, new_comments):

    updated_comments = calculate_revision_updates(
        HashableComment, file_obj.comments, new_comments, ["text", "sort_pos"]
    )
    # add updated comments
    file_obj.comments += updated_comments


def update_file_markers(file_obj, new_markers):

    updated_markers = calculate_revision_updates(
        HashableMarker, file_obj.markers, new_markers, ["marker_class"]
    )
    # add updated comments
    file_obj.markers += updated_markers


@bp.route("/save_editor_data", methods=["POST"])
@admin_required()
def bug_save_editor_data():
    if request.method != "POST":
        return create_json_response("Accepting only POST requests.", 400)

    try:
        vulnerability_details = VulnerabilityDetails()
        vulnerability_details.validate_and_simplify_id()
    except InvalidIdentifierException as ex:
        return create_json_response(str(ex), 400)
    vuln_view = vulnerability_details.vulnerability_view

    if not vuln_view:
        return create_json_response("Please create an entry first", 404)

    if not vuln_view.master_commit:
        current_app.logger.error(
            f"Vuln (id: {vuln_view.id}) has no linked Git commits!"
        )
        return create_json_response("Entry has no linked Git link!", 404)

    ensure(ANNOTATE, vulnerability_details.get_vulnerability())

    master_commit = vulnerability_details.get_master_commit()

    old_files = master_commit.repository_files
    current_app.logger.debug("%d old files", len(old_files))
    # Flush any old custom content of this vulnerability first.
    new_files = []
    for file in request.get_json():
        for old_file in old_files:
            if old_file.file_path == file["path"] or old_file.file_hash == file["hash"]:
                current_app.logger.debug(
                    "Found old file: %s", (file["path"], file["hash"], file["name"])
                )
                file_obj = old_file
                break
        else:
            current_app.logger.debug(
                "Creating new file: %s", (file["path"], file["hash"], file["name"])
            )
            file_obj = RepositoryFiles(
                file_name=file["name"],
                file_path=file["path"],
                file_patch="DEPRECATED",
                file_hash=file["hash"],
            )
        # Create comment objects.
        new_comments = []
        for comment in file["comments"]:
            comment_obj = RepositoryFileComments(
                row_from=comment["row_from"],
                row_to=comment["row_to"],
                text=comment["text"],
                sort_pos=comment["sort_pos"],
                creator=g.user,
            )
            new_comments.append(comment_obj)
        update_file_comments(file_obj, new_comments)
        # Create marker objects.
        new_markers = []
        for marker in file["markers"]:
            marker_obj = RepositoryFileMarkers(
                row_from=marker["row_from"],
                row_to=marker["row_to"],
                column_from=marker["column_from"],
                column_to=marker["column_to"],
                marker_class=marker["class"],
                creator=g.user,
            )
            new_markers.append(marker_obj)
        update_file_markers(file_obj, new_markers)
        new_files.append(file_obj)

    current_app.logger.debug("Setting %d files", len(new_files))
    master_commit.repository_files = new_files

    # Update / Insert entries into the database.
    db.session.commit()
    return create_json_response("Update successful.")
