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

import datetime
import json
import logging

from typing import Iterable, Optional, TYPE_CHECKING, Tuple

import marshmallow

from bouncer.constants import READ, UPDATE, MANAGE, ALL, DELETE  # type: ignore
from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    Enum,
    String,
    Text,
    ForeignKey,
    Index,
    DateTime,
    func,
    UniqueConstraint,
    Table,
    PrimaryKeyConstraint,
)
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, deferred, joinedload

from app.exceptions import InvalidIdentifierException

from data.utils import populate_models
from data.models.base import MainBase, ma
from data.models.user import User, PredefinedRoles

from lib.statemachine import StateMachine, transition, event
from lib.vcs_management import get_vcs_handler, get_vcs_handler_by_repo_hash

if TYPE_CHECKING:
    from data.models.nvd import Nvd  # pylint: disable=ungrouped-imports,cyclic-import

LOG = logging.getLogger(__name__)

APPROVE = "APPROVE"
ASSIGN = "ASSIGN"
REJECT = "REJECT"
ANNOTATE = "ANNOTATE"


def copy_obj(obj):
    # pylint: disable=broad-except
    copy = type(obj)()
    for col in obj.__table__.columns:
        try:
            copy.__setattr__(col.name, getattr(obj, col.name))
        except Exception:  # nosec
            continue
    # Unset all base elements like primary keys and
    # creation / modification time stamps.
    for col in MainBase.__dict__:
        if "__" in col:
            continue
        try:
            copy.__setattr__(col, None)
        except Exception:  # nosec
            continue
    return copy


class VulnerabilityState(StateMachine):
    NEW = 0
    NEEDS_IMPROVEMENT = 1
    READY = 2
    IN_REVIEW = 3
    REVIEWED = 4
    PUBLISHED = 5
    ARCHIVED = 6

    def __init__(self, vulnerability):
        super().__init__()
        self._vulnerability = vulnerability
        self.current_state = vulnerability.state

    @event(NEW)
    def on_new(self):  # pylint: disable=no-self-use
        LOG.info("Vulnerability entered NEW state")

    new_to_ready = transition(NEW, READY)()
    needs_improvement_to_ready = transition(NEEDS_IMPROVEMENT, READY)()
    in_review_to_reviewed = transition(IN_REVIEW, REVIEWED)()
    reviewed_to_needs_improvement = transition(REVIEWED, NEEDS_IMPROVEMENT)()
    published_to_archived = transition(PUBLISHED, ARCHIVED)()

    @transition(REVIEWED, PUBLISHED)
    def check_publishing_possible(self, current_state, next_state):
        del current_state, next_state
        # TODO: check for merge conflicts or other issues
        return self._vulnerability.version is not None

    @transition(READY, READY)
    def check_can_update_proposal(
        self, current_state, next_state
    ):  # pylint: disable=no-self-use
        del current_state, next_state
        # Ready state means that no new reviewer is reviewing this.
        # The entry can be freely updated by the author in the meantime.
        return True

    @transition(IN_REVIEW, READY)
    def check_return_to_pool(self, current_state, next_state):
        del current_state, next_state
        return self._vulnerability.reviewer is None

    @transition(IN_REVIEW, NEEDS_IMPROVEMENT)
    def check_pushback(self, current_state, next_state):
        del current_state, next_state
        return (
            bool(self._vulnerability.review_feedback)
            and self._vulnerability.reviewer is not None
        )

    @transition(READY, IN_REVIEW)
    def check_accept_review(self, current_state, next_state):
        del current_state, next_state
        return self._vulnerability.reviewer is not None

    @transition(PUBLISHED, ARCHIVED)
    def check_archiving_possible(self, current_state, next_state):
        del current_state, next_state
        other_published_entry_exists = Vulnerability.query.filter(
            Vulnerability.id != self._vulnerability.id,
            Vulnerability.vcdb_id == self._vulnerability.vcdb_id,
            Vulnerability.state == VulnerabilityState.PUBLISHED,
        ).first()
        return bool(other_published_entry_exists)


class RevisionMixin:
    revision = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)
    archived_at = Column(DateTime)

    def archive(self):
        self.active = False
        self.archived_at = datetime.datetime.utcnow()

    def to_json(self):
        """Serialize object properties as dict."""
        return {
            "revision": self.revision,
            "active": self.active,
            "archived_at": self.archived_at,
        }


class MarshmallowBase(ma.SQLAlchemyAutoSchema):

    __abstract__ = True

    class Meta:
        exclude: Iterable[str] = ("id", "date_created", "date_modified")


class CreatorSchema(MarshmallowBase):
    class Meta:
        model = User
        fields: Iterable[str] = ("name", "avatar", "profile_link")


class RepositoryFileMarkers(RevisionMixin, MainBase):
    __tablename__ = "repository_file_markers"
    row_from = Column(Integer)
    row_to = Column(Integer)
    column_from = Column(Integer)
    column_to = Column(Integer)
    marker_class = Column(String(100), nullable=False)
    repository_file_id = Column(Integer, ForeignKey("repository_files.id"))
    creator_id = Column(Integer, ForeignKey(User.id), nullable=True)
    creator = relationship(User, lazy="joined", uselist=False)

    def copy(self):
        new_marker = copy_obj(self)
        return new_marker


class RepositoryFileMarkersSchema(MarshmallowBase):
    class Meta(MarshmallowBase.Meta):
        model = RepositoryFileMarkers

    creator = marshmallow.fields.Nested(CreatorSchema)


class RepositoryFileComments(RevisionMixin, MainBase):
    __tablename__ = "repository_file_comments"
    row_from = Column(Integer)
    row_to = Column(Integer)
    text = Column(Text, nullable=False)
    sort_pos = Column(Integer)
    repository_file_id = Column(Integer, ForeignKey("repository_files.id"))
    creator_id = Column(Integer, ForeignKey(User.id), nullable=True)
    creator = relationship(User, lazy="joined", uselist=False)

    def copy(self):
        new_comment = copy_obj(self)
        return new_comment


class RepositoryFileCommentsSchema(MarshmallowBase):
    class Meta(MarshmallowBase.Meta):
        model = RepositoryFileComments
        exclude = ["archived_at", "active"]

    creator = marshmallow.fields.Nested(CreatorSchema)


class RepositoryFiles(MainBase):
    __tablename__ = "repository_files"
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=False)
    file_hash = Column(String(255), nullable=False)
    # A cached version of all file changes for the given commit.
    file_patch = Column(Text, nullable=False)

    markers = relationship(
        RepositoryFileMarkers,
        backref="repository_file",
        cascade="all, delete-orphan",
        primaryjoin=(
            "and_(RepositoryFiles.id==RepositoryFileMarkers.repository_file_id, "
            "RepositoryFileMarkers.active==True)"
        ),
        single_parent=True,
    )

    comments = relationship(
        RepositoryFileComments,
        backref="repository_file",
        cascade="all, delete-orphan",
        primaryjoin=(
            "and_(RepositoryFiles.id==RepositoryFileComments.repository_file_id, "
            "RepositoryFileComments.active==True)"
        ),
        single_parent=True,
    )
    commit_id = Column(Integer, ForeignKey("vulnerability_git_commits.id"))

    def copy(self):
        new_repo_file = copy_obj(self)
        new_repo_file.markers = []
        for marker in self.markers:
            new_repo_file.markers.append(marker.copy())
        new_repo_file.comments = []
        for comment in self.comments:
            new_repo_file.comments.append(comment.copy())
        return new_repo_file


class RepositoryFilesSchema(MarshmallowBase):
    # TODO: Add exlude=[] parameter here to skip redundant date and id fields.
    # pylint: disable=no-member
    file_patch = ma.Method("get_patch")
    markers = ma.Nested(RepositoryFileMarkersSchema, many=True)
    comments = ma.Nested(RepositoryFileCommentsSchema, many=True)
    # pylint: enable=no-member

    @staticmethod
    def get_patch(obj):
        del obj
        return "DEPRECATED"

    class Meta(MarshmallowBase.Meta):
        model = RepositoryFiles


class VulnerabilityResources(MainBase):
    link = Column(String(255), nullable=False)
    vulnerability_details_id = Column(
        Integer, ForeignKey("vulnerability.id"), nullable=False
    )
    vulnerability = relationship(
        "Vulnerability",
        # don't use a list here, otherwise SQLAlchemy
        # is unable to know that it has to autofill
        # the column before inserting
        foreign_keys=vulnerability_details_id,
    )

    def to_json(self):
        """Serialize object properties as dict."""
        return {
            "id": self.id,
            "date_created": self.date_created,
            "date_modified": self.date_modified,
            "link": self.link,
            "vulnerability_details_id": self.vulnerability_details_id,
        }

    def copy(self):
        new_resources = copy_obj(self)
        return new_resources


class VulnerabilityGitCommits(MainBase):
    __tablename__ = "vulnerability_git_commits"

    commit_hash = Column(String(255), nullable=False, index=True)
    _commit_link = Column("commit_link", String(255), nullable=False)
    repo_name = Column(String(255), nullable=False)
    repo_owner = Column(String(255))
    # URL to a *.git Git repository (if applicable).
    _repo_url = Column("repo_url", String(255))
    vulnerability_details_id = Column(
        Integer, ForeignKey("vulnerability.id", name="fk_vuln"), nullable=False
    )
    vulnerability = relationship(
        "Vulnerability", foreign_keys=[vulnerability_details_id]
    )
    # Used to store/cache the repository tree files with hashes.
    tree_cache = deferred(Column(LONGTEXT()))

    repository_files = relationship(
        RepositoryFiles,
        backref="commit",
        cascade="all, delete-orphan",
        single_parent=True,
    )
    # link to comments through RepositoryFiles
    comments = relationship(
        RepositoryFileComments,
        backref="commit",
        secondary=RepositoryFiles.__table__,
        primaryjoin="VulnerabilityGitCommits.id==RepositoryFiles.commit_id",
        secondaryjoin=(
            "and_(RepositoryFiles.id==RepositoryFileComments.repository_file_id,"
            "RepositoryFileComments.active==True)"
        ),
    )
    # link to markers through RepositoryFiles
    markers = relationship(
        RepositoryFileMarkers,
        backref="commit",
        secondary=RepositoryFiles.__table__,
        primaryjoin="VulnerabilityGitCommits.id==RepositoryFiles.commit_id",
        secondaryjoin=(
            "and_(RepositoryFiles.id==RepositoryFileMarkers.repository_file_id,"
            "RepositoryFileMarkers.active==True)"
        ),
    )

    @property
    def num_files(self):
        # TODO: This should be refactored as it is incredibly inefficient.
        #       We should use a count on the database side instead.
        return len(self.repository_files)

    @property
    def num_comments(self):
        # TODO: see comment regarding performance above.
        return len(self.comments)

    @property
    def num_markers(self):
        # TODO: see comment regarding performance above.
        return len(self.markers)

    @property
    def repo_url(self):
        if not self._repo_url:
            # TODO: Refactor this apporach of retrieving github.com urls.
            if self.commit_link and "github.com" in self.commit_link:
                if self.repo_owner and self.repo_name:
                    return f"https://github.com/{self.repo_owner}/{self.repo_name}"  # pylint: disable=line-too-long
        return self._repo_url

    @repo_url.setter
    def repo_url(self, repo_url):
        self._repo_url = repo_url

    @property
    def commit_link(self):
        return self._commit_link

    @commit_link.setter
    def commit_link(self, commit_link):
        # TODO: Recheck link sanitization when other links then GitHub are
        # allowed again. There might be no repo_url set and the commit_link
        # might be just a VCS UI link to the patch. We should still always
        # require a separate repository link and commit hash if it's not a
        # simple Github entry.

        (commit_link, repo_url, commit_hash) = self._parse_commit_link(commit_link)
        self._commit_link = commit_link
        if repo_url:
            self.repo_url = repo_url
        self.commit_hash = commit_hash

    @staticmethod
    def _parse_commit_link(commit_link) -> Tuple[str, Optional[str], Optional[str]]:
        vcs_handler = get_vcs_handler(None, commit_link)
        if not vcs_handler:
            raise InvalidIdentifierException("Please specify a valid commit link")

        return commit_link, vcs_handler.repo_url, vcs_handler.commit_hash

    def __init__(
        self,
        commit_link=None,
        repo_owner=None,
        repo_name=None,
        repo_url=None,
        commit_hash=None,
    ):
        super().__init__()
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        if commit_link:
            (
                commit_link,
                parsed_repo_url,
                parsed_commit_hash,
            ) = self._parse_commit_link(commit_link)

            self.commit_link = commit_link
            if parsed_repo_url is not None:
                repo_url = parsed_repo_url
            if parsed_commit_hash is not None:
                commit_hash = parsed_commit_hash
        if repo_url or commit_hash:
            vcs_handler = get_vcs_handler_by_repo_hash(None, repo_url, commit_hash)
            if not vcs_handler:
                raise InvalidIdentifierException(
                    "Please specify a valid repo_url and commit_hash"
                )
            self.commit_hash = commit_hash
            self.repo_url = repo_url
            if commit_link is None:
                self.commit_link = vcs_handler.commit_link

    def to_json(self):
        """Serialize object properties as dict."""
        return {
            "commit_link": self.commit_link,
            "repo_owner": self.repo_owner,
            "repo_name": self.repo_name,
            "repo_url": self.repo_url,
            "commit_hash": self.commit_hash,
            "relevant_files": self.get_relevant_files(),
        }

    def get_relevant_files(self):
        """Extracts the relevant files from tree_cache"""
        relevant_files = []

        if self.tree_cache is None:
            return relevant_files

        tree = json.loads(self.tree_cache)
        if "commit" in tree:
            commit_data = tree["commit"]
            master_commit_files = commit_data["files"]

            for patched_files in master_commit_files:
                relevant_file_path = "./" + patched_files["path"]
                relevant_files.append(relevant_file_path)

        return relevant_files

    def copy(self):
        new_commit = copy_obj(self)
        new_commit.repository_files = []
        for repo_file in self.repository_files:
            new_commit.repository_files.append(repo_file.copy())
        # N.B. comments and markers are copied in repository_files not here.
        return new_commit


vulnerable_products = Table(
    "vulnerable_products",
    MainBase.metadata,
    Column("vuln_id", Integer, ForeignKey("vulnerability.id")),
    Column("product_id", Integer, ForeignKey("product.id")),
    PrimaryKeyConstraint("vuln_id", "product_id"),
)


class Vulnerability(MainBase):  # pylint: disable=too-many-public-methods
    # __fulltext_columns__ = ('comment',)
    __tablename__ = "vulnerability"
    vcdb_id = Column(Integer, default=None, nullable=True)
    version = Column(Integer, default=None, nullable=True)
    prev_version = Column(Integer, default=None, nullable=True)
    state = Column(
        Enum(VulnerabilityState), default=VulnerabilityState.NEW, nullable=False
    )
    reviewer_id = Column(
        Integer, ForeignKey(User.id, name="fk_reviewer_id"), nullable=True
    )
    reviewer = relationship(User, foreign_keys=[reviewer_id])
    review_feedback = Column(Text)
    feedback_reviewer_id = Column(
        Integer,
        ForeignKey(User.id, name="fk_feedback_reviewer_id", ondelete="RESTRICT"),
        nullable=True,
    )
    feedback_reviewer = relationship(User, foreign_keys=[feedback_reviewer_id])
    comment = Column(Text, nullable=False)
    date_created = Column(DateTime, default=func.current_timestamp(), index=True)
    exploit_exists = Column(Boolean, default=False)
    # N.B. Don't use a ForeignKey constraint on NVD here as the nvd data might
    # be updated dynamically (e.g. row deleted and then added by
    # go-cve-dictionary).
    cve_id = Column(String(255), nullable=True, index=True)
    UniqueConstraint(vcdb_id, version, name="uk_vcdb_id_version")
    creator_id = Column(
        Integer, ForeignKey(User.id, ondelete="RESTRICT"), nullable=True
    )
    creator = relationship(User, foreign_keys=[creator_id])

    resources = relationship(
        VulnerabilityResources,
        cascade="all, delete-orphan",
        single_parent=True,
    )

    commits = relationship(
        VulnerabilityGitCommits,
        cascade="all, delete-orphan",
        single_parent=True,
        lazy="joined",
    )

    nvd = relationship(
        "Nvd",
        backref="vulns",
        primaryjoin="remote(Nvd.cve_id) == foreign(Vulnerability.cve_id)",
    )

    products = relationship(
        "Product",
        secondary=vulnerable_products,
        backref="vulnerabilities",
    )

    _has_annotations = None

    def user_can_read(self, user: User):
        return self.state == VulnerabilityState.PUBLISHED or self.is_creator(user)

    def user_can_update(self, user: User):
        return self.is_creator(user)

    def user_can_annotate(self, user: User):
        return False  # disable for now
        return self.is_creator(user)  # pylint: disable=unreachable

    def user_can_delete(self, user: User):
        return (
            self.is_creator(user)
            and self.state
            in (
                VulnerabilityState.READY,
                VulnerabilityState.NEW,
                VulnerabilityState.NEEDS_IMPROVEMENT,
            )
            or user.is_admin()
            and self.state == VulnerabilityState.ARCHIVED
        )

    def reviewer_can_read(self, user: User):
        return (
            self.state == VulnerabilityState.READY
            or self.state
            in (
                VulnerabilityState.IN_REVIEW,
                VulnerabilityState.REVIEWED,
                VulnerabilityState.ARCHIVED,
            )
            and self.is_reviewer(user)
        )

    _permissions = {
        PredefinedRoles.ADMIN: {
            MANAGE: ALL,
        },
        PredefinedRoles.USER: {
            READ: user_can_read,
            UPDATE: user_can_update,
            DELETE: user_can_delete,
            ANNOTATE: user_can_annotate,
        },
        PredefinedRoles.REVIEWER: {
            READ: reviewer_can_read,
            ASSIGN: True,
            APPROVE: True,
            REJECT: True,
        },
    }

    def set_has_annotations(self, status: bool = True):
        self._has_annotations = status

    @hybrid_property
    def has_annotations(self):
        if self._has_annotations is not None:
            return self._has_annotations

        if self.commits:
            for commit in self.commits:
                if commit.comments:
                    self._has_annotations = True
                    return True
        return False

    @has_annotations.expression  # type: ignore[no-redef]
    def has_annotations(self):
        return self.commits.any(VulnerabilityGitCommits.comments.any())

    @property
    def master_commit(self):
        # TODO: refactor assumption that the first commit is the "master" one!
        if self.commits and self.commits[0].commit_link:
            return self.commits[0]
        return None

    def __repr__(self):
        return f"Vulnerability Info({vars(self)})"

    @classmethod
    def get_by_vcdb_id(
        cls, id: str, published_only: bool = True
    ):  # pylint: disable=redefined-builtin
        state_filter = None
        if published_only:
            state_filter = VulnerabilityState.PUBLISHED
        return (
            cls.query.filter_by(vcdb_id=id, state=state_filter)
            .options(default_vuln_view_options)
            .order_by(cls.version.desc())
            .first()
        )

    @classmethod
    def get_by_id(cls, id: str):  # pylint: disable=redefined-builtin
        return cls.query.filter_by(id=id).options(default_vuln_view_options).first()

    @classmethod
    def get_by_cve_id(cls, cve_id: str, published_only: bool = True):
        state_filter = None
        if published_only:
            state_filter = VulnerabilityState.PUBLISHED
        return (
            cls.query.filter_by(cve_id=cve_id, state=state_filter)
            .options(default_vuln_view_options)
            .first()
        )

    @classmethod
    def get_by_commit_hash(cls, commit_hash: str):
        return (
            cls.query.join(Vulnerability.commits, aliased=True)
            .filter_by(commit_hash=commit_hash)
            .options(default_vuln_view_options)
            .first()
        )

    def get_contributors(self):
        return User.query.join(Vulnerability.creator).filter(
            Vulnerability.vcdb_id == self.vcdb_id, Vulnerability.is_published
        )

    def to_json(self):
        """Prepare object for Json serialisation."""
        products = [{"vendor": v, "product": p} for v, p in self.nvd.get_products()]
        cwes = [{"id": c.cwe_id, "name": c.cwe_name} for c in self.nvd.cwes]
        return {
            "comment": self.comment,
            "cve_id": self.cve_id,
            "cwes": cwes,
            "description": self.nvd.description,
            "exploit_exists": self.exploit_exists,
            "has_annotations": self.has_annotations,
            "is_processed": True,
            "langs": self.nvd.get_languages(),
            "master_commit": self.master_commit.to_json(),
            "products": products,
            "references": [l.link for l in self.nvd.references],
            "score": self.nvd.score,
        }

    def to_json_full(self):
        """Serialize object properties as dict."""
        data = self.to_json()
        data["resources"] = [
            r.to_json() for r in self.resources if self.resources is not None
        ]
        data["commits"] = [
            c.to_json() for c in self.commits if self.commits is not None
        ]
        data["nvd"] = self.nvd.to_json_raw_data() if self.nvd is not None else None
        data["creator"] = self.creator.to_json() if self.creator is not None else None
        data["date_created"] = self.date_created
        data["date_modified"] = self.date_modified

        return data

    def update_state(self, new_state):
        state_machine = VulnerabilityState(self)
        state_machine.next_state(new_state)
        self.state = new_state

    @hybrid_property
    def is_new(self):
        return self.state == VulnerabilityState.NEW

    @hybrid_property
    def is_published(self):
        return self.state == VulnerabilityState.PUBLISHED

    @hybrid_property
    def is_archived(self):
        return self.state == VulnerabilityState.ARCHIVED

    @hybrid_property
    def needs_improvement(self):
        return self.state == VulnerabilityState.NEEDS_IMPROVEMENT

    @hybrid_property
    def is_reviewable(self):
        return self.state == VulnerabilityState.READY

    @hybrid_property
    def is_in_review(self):
        return self.state == VulnerabilityState.IN_REVIEW

    @hybrid_property
    def is_publishable(self):
        return self.state == VulnerabilityState.REVIEWED

    def is_reviewer(self, reviewer):
        return self.reviewer == reviewer

    def is_creator(self, creator):
        return self.creator == creator

    @hybrid_property
    def has_feedback(self):
        return bool(self.review_feedback)

    def make_reviewable(self):
        self.update_state(VulnerabilityState.READY)

    def accept_review(self, reviewer):
        self.reviewer = reviewer
        self.update_state(VulnerabilityState.IN_REVIEW)

    def deny_review(self):
        self.reviewer = None
        self.update_state(VulnerabilityState.READY)

    def accept_change(self):
        self.update_state(VulnerabilityState.REVIEWED)

    def deny_change(self, reviewer, reason):
        self.feedback_reviewer = reviewer
        self.review_feedback = reason
        self.update_state(VulnerabilityState.NEEDS_IMPROVEMENT)

    def archive_entry(self):
        self.update_state(VulnerabilityState.ARCHIVED)

    def return_to_review_pool(self):
        self.reviewer = None
        self.update_state(VulnerabilityState.READY)

    def publish_change(self):
        self.version = self.next_version_number()
        # TODO: Assign a new vcdb_id if required at this point.
        #       This is mostly relevant for fully new entry proposals.
        self.update_state(VulnerabilityState.PUBLISHED)

    def next_version_number(self):
        prev_version = (
            Vulnerability.query.filter_by(vcdb_id=self.vcdb_id)
            .with_entities(func.max(Vulnerability.version))
            .first()[0]
        )
        if not prev_version:
            prev_version = 0
        return prev_version + 1

    @staticmethod
    def get_num_proposals_action_required(user):  # pylint: disable=invalid-name
        return Vulnerability.query.filter(
            Vulnerability.creator == user,
            Vulnerability.state.in_(
                [VulnerabilityState.NEW, VulnerabilityState.NEEDS_IMPROVEMENT]
            ),
        ).count()

    @staticmethod
    def get_num_proposals_pending(user):
        return Vulnerability.query.filter(
            Vulnerability.creator == user,
            Vulnerability.state.in_(
                [
                    VulnerabilityState.READY,
                    VulnerabilityState.IN_REVIEW,
                    VulnerabilityState.REVIEWED,
                ]
            ),
        ).count()

    @staticmethod
    def get_num_proposals_publishing_pending():  # pylint: disable=invalid-name
        return Vulnerability.query.filter(
            Vulnerability.state == VulnerabilityState.REVIEWED
        ).count()

    @staticmethod
    def get_num_proposals_unassigned():
        return Vulnerability.query.filter(
            Vulnerability.state == VulnerabilityState.READY
        ).count()

    @staticmethod
    def get_num_proposals_assigned():
        return Vulnerability.query.filter(
            Vulnerability.state == VulnerabilityState.IN_REVIEW
        ).count()

    @staticmethod
    def get_num_proposals_assigned_to(user):
        return Vulnerability.query.filter(
            Vulnerability.reviewer == user,
            Vulnerability.state == VulnerabilityState.IN_REVIEW,
        ).count()

    def copy(self):
        new_vuln = copy_obj(self)
        new_vuln.commits = []
        for commit in self.commits:
            new_vuln.commits.append(commit.copy())
        for resource in self.resources:
            new_vuln.resources.append(resource.copy())
        # N.B. We never copy NVD data as it's supposed to stay read only.
        return new_vuln


class Product(MainBase):
    __tablename__ = "product"
    vendor = Column(String(255), nullable=False)
    product = Column(String(255), nullable=False)
    is_open_source = Column(Boolean, nullable=True)

    def to_json(self):
        """Serialize object properties as dict."""
        return {"vendor": self.vendor, "product": self.product}


Index("idx_product_main", Product.vendor, Product.product, unique=True)

# TODO: Refactor these filters. We might want to use them as lazy loads instead
# Currently, querying like this eats up quite some time.
# See for example: /CVE-2014-0160
# pylint: disable=invalid-name
load_relationships1 = (
    joinedload(Vulnerability.commits)
    .joinedload(VulnerabilityGitCommits.repository_files)
    .joinedload(RepositoryFiles.comments)
)

load_relationships2 = (
    joinedload(Vulnerability.commits)
    .joinedload(VulnerabilityGitCommits.repository_files)
    .joinedload(RepositoryFiles.markers)
)

load_relationships3 = (
    joinedload(Vulnerability.commits)
    .joinedload(VulnerabilityGitCommits.comments)
    .joinedload(RepositoryFileComments.repository_file)
)

default_vuln_view_options = [
    load_relationships1,
    load_relationships2,
    load_relationships3,
]
# pylint: enable=invalid-name

# must be set after all definitions
__all__ = populate_models(__name__)
