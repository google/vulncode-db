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

from lib.vcs_handler.vcs_handler import (
    VcsHandler,
    VULN_ID_PLACEHOLDER,
    PATH_PLACEHOLDER,
    HASH_PLACEHOLDER,
    CommitStats,
    CommitFilesMetadata,
    CommitMetadata,
)
import os

from app.exceptions import InvalidIdentifierException
from flask import url_for, jsonify

from io import BytesIO
from unidiff import PatchSet
from dulwich.repo import Repo

# Packages like GitPython are not supported on GAE since they make use of
# c libraries or other system utilities. We only use such packages on other
# sytems like GCE VMs.
try:
    from git import Repo as GitPythonRepo
except ImportError:
    pass

from urllib.parse import urlparse
import dulwich.errors
import dulwich.repo
import dulwich.client
import dulwich.config
import dulwich.objects
from dulwich.patch import write_tree_diff
from dulwich import porcelain
import re

REPO_PATH = "vulnerable_code/"

# [SCHEMA]://[HOST]/[PATH].git#[COMMIT_HASH]
# [SCHEMA]://[HOST]/[PATH].git@[COMMIT_HASH]
URL_RE = re.compile(
    r"^(?P<url>.*/(?P<name>[^/]+).git)(?:[#@](?P<commit>[a-fA-Z0-9]{7,}))?$")


class GitTreeElement:
    sha = None
    path = None
    type = None


def _file_list_dulwich(repo, tgt_env, recursive=False):
    """Get file list using dulwich"""
    def _traverse(tree, repo_obj, blobs, prefix):
        """Traverse through a dulwich Tree object recursively, accumulating all the blob paths within it in the "blobs" list"""
        for item in list(tree.items()):
            try:
                obj = repo_obj.get_object(item.sha)
            except KeyError:
                # Skip "commit" objects which are links to submodules.
                continue
            foo = GitTreeElement()
            foo.sha = item.sha.decode("ascii")
            foo.path = os.path.join(prefix, item.path.decode("utf8"))
            if isinstance(obj, dulwich.objects.Blob):
                foo.type = "blob"
                blobs.append(foo)
            elif isinstance(obj, dulwich.objects.Tree):
                foo.type = "tree"
                blobs.append(foo)
                # Check whether to fetch more than the most upper layer.
                if recursive:
                    _traverse(obj, repo_obj, blobs, foo.path)

    tree = repo.get_object(tgt_env.tree)
    if not isinstance(tree, dulwich.objects.Tree):
        return []
    blobs = []
    if len(tree):
        _traverse(tree, repo, blobs, "")
    return blobs


class GitRepoHandler(VcsHandler):
    def __init__(self, app, resource_url):
        """Initializes the questionnaire object."""
        super(GitRepoHandler, self).__init__(app, resource_url)
        self.repo = None
        self.parseResourceURL(resource_url)

    def parseResourceURL(self, resource_url):
        if not resource_url or not urlparse(resource_url.replace("@", "#")):
            raise InvalidIdentifierException("Please provide a valid URL.")

        matches = URL_RE.search(resource_url)
        if not matches:
            raise InvalidIdentifierException(
                "Please provide a valid ([SCHEMA]://[HOST]/[PATH].git#[COMMIT_HASH]) Git Repo link."
            )
        self.repo_name = matches.group("name")
        self.repo_name = os.path.basename(self.repo_name)
        self.repo_url = matches.group("url")
        self.commit_hash = matches.group("commit")
        self.commit_link = resource_url

    def _getPatchDeltas(self, patch_set):
        patched_files = {}
        for patched_file in patch_set:
            patched_files[patched_file.path] = []
            for hunk in patched_file:
                for line in hunk:
                    if line.is_context:
                        continue
                    patched_files[patched_file.path].append(vars(line))
        return patched_files

    def _getPatcheSet(self, old_commit, new_commit):

        patch_diff = BytesIO()
        write_tree_diff(patch_diff, self.repo.object_store, old_commit.tree,
                        new_commit.tree)
        patch_diff.seek(0)
        patch = PatchSet(patch_diff, encoding="utf-8")
        return patch

    def _fetchOrInitRepo(self):
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
            self._logError(
                f"Invalid path: {self.repo_url} + {self.repo_name} => {repo_path}"
            )
            raise Exception("Can't clone repo. Invalid repository.")

        if not os.path.isdir(repo_path):
            # Using GitPython here since Dulwich was throwing weird errors like:
            # "IOError: Not a gzipped file" when fetching resources like:
            # https://git.centos.org/r/rpms/dhcp.git
            if not GitPythonRepo.clone_from(
                    self.repo_url, repo_path, bare=True):
                self._logError(f"Can't clone repo {self.repo_name}.")
                raise Exception("Can't clone repo.")

        self.repo = Repo(repo_path)
        return True

    def getFileProviderUrl(self):
        return url_for(
            "vuln.file_provider",
            item_hash=HASH_PLACEHOLDER,
            vuln_id=VULN_ID_PLACEHOLDER,
        )

    def getRefFileProviderUrl(self):
        return url_for(
            "vuln.file_provider",
            item_path=PATH_PLACEHOLDER,
            item_hash=HASH_PLACEHOLDER,
            vuln_id=VULN_ID_PLACEHOLDER,
        )

    def getFileUrl(self):
        # A custom repository doesn't necessarily have a VCS web interface.
        return ""

    def getTreeUrl(self):
        # A custom repository doesn't necessarily have a VCS web interface.
        return ""

    def _fetch_remote(self):
        repo = GitPythonRepo(self.repo.path)
        repo.remote().fetch("+refs/heads/*:refs/remotes/origin/*")

    def _getFilesMetadata(self, patch_set):
        files_metadata = []
        for file in patch_set:
            status = "modified"
            if file.is_added_file:
                status = "added"
            elif file.is_removed_file:
                status = "removed"

            file_metadata = CommitFilesMetadata(file.path, status, file.added,
                                                file.removed)
            files_metadata.append(file_metadata)
        return files_metadata

    def _getPatchStats(self, patch_set):
        additions = 0
        deletions = 0
        for file in patch_set:
            additions += file.added
            deletions += file.removed
        total = additions + deletions
        return CommitStats(additions, deletions, total)

    def _getItemHashFromPath(self, repo_hash, item_path):
        git_tree = _file_list_dulwich(self.repo, self.repo[repo_hash], True)
        for f in git_tree:
            if f.path == item_path:
                return f.sha
        return None

    def fetchCommitData(self, commit_hash):
        if not commit_hash:
            commit_hash = self.commit_hash

        if not commit_hash:
            self._logError(
                f"No commit_hash provided for repo URL: {self.repo_url}.")
            raise Exception("Please provide a commit_hash.")

        # py 3 compatiblity. Dulwich expects hashes to be bytes
        if not hasattr(commit_hash, "decode"):
            commit_hash = commit_hash.encode("ascii")

        if not self._fetchOrInitRepo():
            return None

        if commit_hash not in self.repo:
            self._logError(
                f"Can't find commit_hash {commit_hash} in given repo. Fetching updates and retry."
            )
            self._fetch_remote()

        if commit_hash not in self.repo:
            self._logError(
                f"Can't find commit_hash {commit_hash} in given repo. Cancelling request."
            )
            raise Exception("Can't find commit_hash in given repo.")

        commit = self.repo[commit_hash]
        commit_parents = commit.parents
        parent_commit_hash = commit_parents[0]
        parent_commit = self.repo[parent_commit_hash]

        git_tree = _file_list_dulwich(self.repo, parent_commit)
        patch_set = self._getPatcheSet(parent_commit, commit)
        patch_deltas = self._getPatchDeltas(patch_set)

        commit_stats = self._getPatchStats(patch_set)
        patch_files_metadata = self._getFilesMetadata(patch_set)

        # patched_files = self._ParsePatchPerFile(commit.files)
        patched_files = {}
        for file in patch_files_metadata:
            if file.status == "added":
                patched_file_sha = self._getItemHashFromPath(
                    commit_hash, file.path)
            else:
                patched_file_sha = self._getItemHashFromPath(
                    parent_commit_hash, file.path)
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
        data = self._CreateData(git_tree, patched_files, commit_metadata)

        json_content = jsonify(data)
        return json_content

    def getFileContent(self, item_sha, item_path=None):
        if not self._fetchOrInitRepo():
            return None

        # py 3 compatiblity. Dulwich expects hashes to be bytes
        if not hasattr(item_sha, "decode"):
            item_sha = item_sha.encode("ascii")

        # Fetch by item path and target environment.
        if item_path:
            git_tree = _file_list_dulwich(self.repo, self.repo[item_sha], True)
            for f in git_tree:
                if f.path == item_path:
                    target_sha = f.sha
                    return self.repo.object_store[target_sha].data
        else:
            if item_sha in self.repo.object_store:
                return self.repo.object_store[item_sha].data

        return None
