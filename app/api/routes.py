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

from flask import Blueprint, request, current_app, g, jsonify

from app.auth.routes import login_required, admin_required
from app.exceptions import InvalidIdentifierException
from app.vulnerability.views.details import VulnerabilityDetails

from data.database import DEFAULT_DATABASE
from data.models import (
    RepositoryFilesSchema,
    RepositoryFileComments,
    RepositoryFileMarkers,
    RepositoryFiles,
)
from lib.utils import create_json_response

bp = Blueprint("api", __name__, url_prefix="/api")
db = DEFAULT_DATABASE.db


def calculate_revision_updates(wrapper, old, new, attrs):
    old_dict = dict(list(zip(list(map(wrapper, old)), old)))
    old_keys = frozenset(list(old_dict.keys()))
    new_dict = dict(list(zip(list(map(wrapper, new)), new)))
    new_keys = frozenset(list(new_dict.keys()))

    intersection = old_keys & new_keys
    current_app.logger.debug(
        f"{len(old_keys)} old, {len(new_keys)} new, {len(intersection)} intersecting"
    )
    # current_app.logger.debug(f'{old_keys} old, {new_keys} new, {intersection} intersecting')

    # archive removed comments
    for k in old_keys - new_keys:
        o = old_dict[k]
        current_app.logger.debug(f"Archiving {k!s}")
        o.archive()

    # filter new comments
    updated_comments = [new_dict[k] for k in new_keys - old_keys]
    for k in intersection:
        o = old_dict[k]
        n = new_dict[k]

        # no changes
        for attr in attrs:
            if getattr(o, attr) != getattr(n, attr):
                break
        else:
            current_app.logger.debug(f"No changes for {k!s}")
            continue
        # archive old version
        current_app.logger.debug(f"Archiving {k!s}")
        o.archive()
        n.revision = o.revision + 1
        updated_comments.append(n)
    return updated_comments


class Hashable(object):
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
        super(HashableComment, self).__init__(comment, lambda c:
                                              (c.row_from, c.row_to))

    def __str__(self):
        return f"comment @ {self.value}"


class HashableMarker(Hashable):
    def __init__(self, marker):
        super(HashableMarker, self).__init__(
            marker, lambda m:
            (m.row_from, m.row_to, m.column_from, m.column_to))

    def __str__(self):
        return "marker @ {0.row_from}:{0.column_from} - {0.row_to}:{0.column_to}".format(
            self.item)


def update_file_comments(file_obj, new_comments):

    updated_comments = calculate_revision_updates(HashableComment,
                                                  file_obj.comments,
                                                  new_comments,
                                                  ["text", "sort_pos"])
    # add updated comments
    file_obj.comments += updated_comments


def update_file_markers(file_obj, new_markers):

    updated_markers = calculate_revision_updates(HashableMarker,
                                                 file_obj.markers, new_markers,
                                                 ["marker_class"])
    # add updated comments
    file_obj.markers += updated_markers


@bp.route("/save_editor_data", methods=["POST"])
@admin_required()
def bug_save_editor_data():
    try:
        vulnerability_details = VulnerabilityDetails()
        vulnerability_details.validate()
    except InvalidIdentifierException as e:
        return create_json_response(str(e), 400)
    vuln_view = vulnerability_details.vulnerability_view

    if request.method == "POST":
        if not vuln_view:
            return create_json_response("Please create an entry first", 404)

        if not vuln_view.master_commit:
            current_app.logger.error(
                f"Vuln (id: {vuln_view.id}) has no linked Git commits!")
            return create_json_response("Entry has no linked Git link!", 404)

        master_commit = vulnerability_details.getMasterCommit()

        # print("DATA: {request.json}"
        old_files = master_commit.repository_files
        current_app.logger.debug("%d old files", len(old_files))
        # Flush any old custom content of this vulnerability first.
        new_files = []
        for file in request.get_json():
            for of in old_files:
                if of.file_path == file["path"] or of.file_hash == file["hash"]:
                    current_app.logger.debug(
                        "Found old file: %s",
                        (file["path"], file["hash"], file["name"]))
                    file_obj = of
                    break
            else:
                current_app.logger.debug(
                    "Creating new file: %s",
                    (file["path"], file["hash"], file["name"]))
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
    return create_json_response("Accepting only POST requests.", 400)
