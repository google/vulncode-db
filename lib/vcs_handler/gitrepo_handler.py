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
import os
import re

from io import BytesIO
from urllib.parse import urlparse

import dulwich.errors  # type: ignore
import dulwich.repo  # type: ignore
import dulwich.client  # type: ignore
import dulwich.config  # type: ignore
import dulwich.objects  # type: ignore

from dulwich.patch import write_tree_diff  # type: ignore
from dulwich.repo import Repo
from flask import url_for, jsonify
from unidiff import PatchSet  # type: ignore
from lib.vcs_handler.vcs_handler import (
    VcsHandler,
    VCDB_ID_PLACEHOLDER,
    PATH_PLACEHOLDER,
    HASH_PLACEHOLDER,
    CommitStats,
    CommitFilesMetadata,
    CommitMetadata,
)

# Packages like GitPython are not supported on GAE since they make use of
# c libraries or other system utilities. We only use such packages on other
# sytems like GCE VMs.
try:
    from git import Repo as GitPythonRepo  # type: ignore
except ImportError:
    pass

from app.exceptions import InvalidIdentifierException

REPO_PATH = "vulnerable_code/"

# [SCHEMA]://[HOST]/[PATH].git
BASE_URL_RE = re.compile(r"^(?P<url>.*/(?P<name>[^/]+).git)$")
# [SCHEMA]://[HOST]/[PATH].git#[COMMIT_HASH]
# [SCHEMA]://[HOST]/[PATH].git@[COMMIT_HASH]
URL_RE = re.compile(BASE_URL_RE.pattern[:-1] + r"(?:[#@](?P<commit>[a-fA-Z0-9]{7,}))?$")


class GitTreeElement:
    sha = None
    path = None
    type = None


def _file_list_dulwich(repo, tgt_env, recursive=False):
    """Get file list using dulwich"""

    def _traverse(tree, repo_obj, blobs, prefix):
        """Traverse through a dulwich Tree object recursively, accumulating all
        the blob paths within it in the "blobs" list"""
        for item in list(tree.items()):
            try:
                obj = repo_obj.get_object(item.sha)
            except KeyError:
                # Skip "commit" objects which are links to submodules.
                continue
            elem = GitTreeElement()
            elem.sha = item.sha.decode("ascii")
            elem.path = os.path.join(prefix, item.path.decode("utf8"))
            if isinstance(obj, dulwich.objects.Blob):
                elem.type = "blob"
                blobs.append(elem)
            elif isinstance(obj, dulwich.objects.Tree):
                elem.type = "tree"
                blobs.append(elem)
                # Check whether to fetch more than the most upper layer.
                if recursive:
                    _traverse(obj, repo_obj, blobs, elem.path)

    tree = repo.get_object(tgt_env.tree)
    if not isinstance(tree, dulwich.objects.Tree):
        return []
    blobs = []
    if len(tree) > 0:
        _traverse(tree, repo, blobs, "")
    return blobs


class GitRepoHandler(VcsHandler):
    def __init__(self, app, resource_url=None):
        """Initializes the questionnaire object."""
        super().__init__(app, resource_url)
        self.repo = None
        if resource_url is not None:
            self.parse_resource_url(resource_url)

    def parse_resource_url(self, resource_url):
        if not resource_url or not urlparse(resource_url.replace("@", "#")):
            raise InvalidIdentifierException("Please provide a valid URL.")

        matches = URL_RE.search(resource_url)
        if not matches:
            raise InvalidIdentifierException(
                "Please provide a valid "
                "([SCHEMA]://[HOST]/[PATH].git#[COMMIT_HASH]) Git Repo link."
            )
        self.repo_name = matches.group("name")
        self.repo_name = os.path.basename(self.repo_name)
        self.repo_url = matches.group("url")
        self.commit_hash = matches.group("commit")
        self.commit_link = resource_url

    def parse_url_and_hash(self, repo_url, commit_hash):
        if not repo_url or not commit_hash:
            raise InvalidIdentifierException("Please provide an URL and hash.")
        if not re.match(r"[a-fA-F0-9]{5,}$", commit_hash):
            raise InvalidIdentifierException(
                "Please provide a valid " "git commit hash (min 5 characters)"
            )
        matches = BASE_URL_RE.search(repo_url)
        if not urlparse(repo_url) or not matches:
            raise InvalidIdentifierException("Please provide a valid git URL")
        self.repo_name = matches.group("name")
        self.repo_name = os.path.basename(self.repo_name)
        self.repo_url = repo_url
        self.commit_hash = commit_hash
        self.commit_link = f"{repo_url}#{commit_hash}"

    @staticmethod
    def _get_patch_deltas(patch_set):
        patched_files = {}
        for patched_file in patch_set:
            patched_files[patched_file.path] = []
            for hunk in patched_file:
                for line in hunk:
                    if line.is_context:
                        continue
                    patched_files[patched_file.path].append(vars(line))
        return patched_files

    def _get_patch_set(self, old_commit, new_commit):

        patch_diff = BytesIO()
        write_tree_diff(
            patch_diff, self.repo.object_store, old_commit.tree, new_commit.tree
        )
        patch_diff.seek(0)
        patch = PatchSet(patch_diff, encoding="utf-8")
        return patch

    def _fetch_or_init_repo(self):
        if self.repo:
            return True
        hostname = urlparse(self.repo_url).hostname
        if not hostname:
            return False
        repo_hostname = os.path.basename(hostname)
        repo_path = os.path.join(
            REPO_PATH,
            repo_hostname,
            # remove any leading slashes
            self.repo_name.replace("..", "__").lstrip("/"),
        )
        repo_path = os.path.normpath(repo_path)
        if not repo_path.startswith(REPO_PATH + repo_hostname):
            self._log_error(
                "Invalid path: %s + %s => %s", self.repo_url, self.repo_name, repo_path
            )
            raise Exception("Can't clone repo. Invalid repository.")

        if not os.path.isdir(repo_path):
            # Using GitPython here since Dulwich was throwing weird errors like:
            # "IOError: Not a gzipped file" when fetching resources like:
            # https://git.centos.org/r/rpms/dhcp.git
            if not GitPythonRepo.clone_from(self.repo_url, repo_path, bare=True):
                self._log_error(f"Can't clone repo {self.repo_name}.")
                raise Exception("Can't clone repo.")

        self.repo = Repo(repo_path)
        return True

    def get_file_provider_url(self):
        return url_for(
            "vuln.file_provider",
            item_hash=HASH_PLACEHOLDER,
            vcdb_id=VCDB_ID_PLACEHOLDER,
        )

    def get_ref_file_provider_url(self):
        return url_for(
            "vuln.file_provider",
            item_path=PATH_PLACEHOLDER,
            item_hash=HASH_PLACEHOLDER,
            vcdb_id=VCDB_ID_PLACEHOLDER,
        )

    def get_file_url(self):
        # A custom repository doesn't necessarily have a VCS web interface.
        return ""

    def get_tree_url(self):
        # A custom repository doesn't necessarily have a VCS web interface.
        return ""

    def _fetch_remote(self):
        repo = GitPythonRepo(self.repo.path)
        repo.remote().fetch("+refs/heads/*:refs/remotes/origin/*")

    @staticmethod
    def _get_files_metadata(patch_set):
        files_metadata = []
        for file in patch_set:
            status = "modified"
            if file.is_added_file:
                status = "added"
            elif file.is_removed_file:
                status = "removed"

            file_metadata = CommitFilesMetadata(
                file.path, status, file.added, file.removed
            )
            files_metadata.append(file_metadata)
        return files_metadata

    @staticmethod
    def _get_patch_stats(patch_set):
        additions = 0
        deletions = 0
        for file in patch_set:
            additions += file.added
            deletions += file.removed
        total = additions + deletions
        return CommitStats(additions, deletions, total)

    def _get_item_hash_from_path(self, repo_hash, item_path):
        git_tree = _file_list_dulwich(self.repo, self.repo[repo_hash], True)
        for file in git_tree:
            if file.path == item_path:
                return file.sha
        return None

    def fetch_commit_data(self, commit_hash):
        if not commit_hash:
            commit_hash = self.commit_hash

        if not commit_hash:
            self._log_error(f"No commit_hash provided for repo URL: {self.repo_url}.")
            raise Exception("Please provide a commit_hash.")

        # py 3 compatiblity. Dulwich expects hashes to be bytes
        if not hasattr(commit_hash, "decode"):
            commit_hash = commit_hash.encode("ascii")

        if not self._fetch_or_init_repo():
            return None

        if commit_hash not in self.repo:
            self._log_error(
                f"Can't find commit_hash {commit_hash} in given repo. "
                "Fetching updates and retry."
            )
            self._fetch_remote()

        if commit_hash not in self.repo:
            self._log_error(
                f"Can't find commit_hash {commit_hash} in given repo. "
                "Cancelling request."
            )
            raise Exception("Can't find commit_hash in given repo.")

        commit = self.repo[commit_hash]
        commit_parents = commit.parents
        parent_commit_hash = commit_parents[0]
        parent_commit = self.repo[parent_commit_hash]

        git_tree = _file_list_dulwich(self.repo, parent_commit)
        patch_set = self._get_patch_set(parent_commit, commit)
        patch_deltas = self._get_patch_deltas(patch_set)

        commit_stats = self._get_patch_stats(patch_set)
        patch_files_metadata = self._get_files_metadata(patch_set)

        # patched_files = self._parse_patch_per_file(commit.files)
        patched_files = {}
        for file in patch_files_metadata:
            if file.status == "added":
                patched_file_sha = self._get_item_hash_from_path(commit_hash, file.path)
            else:
                patched_file_sha = self._get_item_hash_from_path(
                    parent_commit_hash, file.path
                )
            patched_files[file.path] = {
                "status": file.status,
                "sha": patched_file_sha,
                "deltas": patch_deltas[file.path],
            }

        commit_date = commit.commit_time
        commit_metadata = CommitMetadata(
            parent_commit_hash,
            commit_date,
            commit.message,
            commit_stats,
            patch_files_metadata,
        )
        data = self._create_data(git_tree, patched_files, commit_metadata)

        json_content = jsonify(data)
        return json_content

    def get_file_content(self, item_hash, item_path=None):
        if not self._fetch_or_init_repo():
            return None

        # py 3 compatiblity. Dulwich expects hashes to be bytes
        if not hasattr(item_hash, "decode"):
            item_hash = item_hash.encode("ascii")

        # Fetch by item path and target environment.
        if item_path:
            git_tree = _file_list_dulwich(self.repo, self.repo[item_hash], True)
            for file in git_tree:
                if file.path == item_path:
                    target_sha = file.sha
                    return self.repo.object_store[target_sha].data
        else:
            if item_hash in self.repo.object_store:
                return self.repo.object_store[item_hash].data

        return None
