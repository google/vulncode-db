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
import io
import logging
import os
import re

from urllib.parse import urlparse
from github import Github, InputGitTreeElement
from unidiff import PatchSet
from flask import jsonify

from app.exceptions import InvalidIdentifierException
from lib.vcs_handler.vcs_handler import (
    VcsHandler,
    HASH_PLACEHOLDER,
    PATH_PLACEHOLDER,
    CommitStats,
    CommitFilesMetadata,
    CommitMetadata,
)
import lib.utils

CACHE_DIR = "cache/"
"""def get_github_archive_link(owner, repo, hash):

  link =
  'https://github.com/{owner}/{repo}/archive/{hash}.zip'.format(owner=owner,
  repo=repo, hash=hash)
  return link
"""


class GithubHandler(VcsHandler):
    def __init__(self, app, resource_url):
        """Initializes the questionnaire object."""
        super(GithubHandler, self).__init__(app, resource_url)
        # We're currently using DB caching for file tree data.
        self.use_cache = False

        use_token = None
        if app and "GITHUB_API_ACCESS_TOKEN" in app.config:
            use_token = app.config["GITHUB_API_ACCESS_TOKEN"]

        self.github = Github(login_or_token=use_token)
        self.parseResourceURL(resource_url)

    def parseResourceURL(self, resource_url):
        if not resource_url:
            raise InvalidIdentifierException(
                "Please provide a Github commit link.")
        url_data = urlparse(resource_url)
        git_path = url_data.path
        matches = re.match(r"/([^/]+)/([^/]+)/commit/([^/]+)/?$", git_path)
        if (not url_data.hostname or "github.com" not in url_data.hostname
                or not matches):
            raise InvalidIdentifierException(
                "Please provide a valid (https://github.com/{owner}/{repo}/commit/{hash}) commit link."
            )
        self.repo_owner, self.repo_name, self.commit_hash = matches.groups()
        self.commit_link = resource_url

    def _ParsePatchPerFile(self, files):
        patched_files = {}
        # Process all patches provided by Github and save them in a new per file per line representation.
        for patched_file in files:
            patched_files[patched_file.filename] = {
                "status": patched_file.status,
                "sha": patched_file.sha,
                "deltas": [],
            }

            patch_str = io.StringIO()
            patch_str.write("--- a\n+++ b\n")
            if patched_file.patch is not None:
                patch_str.write(patched_file.patch)
            patch_str.seek(0)
            logging.debug(f"Parsing diff\n{patch_str.getvalue()}")
            patch = PatchSet(patch_str, encoding=None)

            for hunk in patch[0]:
                for line in hunk:
                    if line.is_context:
                        continue
                    patched_files[patched_file.filename]["deltas"].append(
                        vars(line))

        return patched_files

    def getFileProviderUrl(self):
        owner = self.repo_owner
        repo = self.repo_name
        return f"https://api.github.com/repos/{owner}/{repo}/git/blobs/{HASH_PLACEHOLDER}"

    def getRefFileProviderUrl(self):
        owner = self.repo_owner
        repo = self.repo_name
        return f"https://api.github.com/repos/{owner}/{repo}/contents/{PATH_PLACEHOLDER}?ref={HASH_PLACEHOLDER}"

    def getFileUrl(self):
        owner = self.repo_owner
        repo = self.repo_name
        commit_hash = self.commit_hash
        return f"https://github.com/{owner}/{repo}/blob/{commit_hash}/"

    def getTreeUrl(self):
        owner = self.repo_owner,
        repo = self.repo_name,
        commit_hash = self.commit_hash
        return f"https://github.com/{owner}/{repo}/tree/{commit_hash}/"

    def _getFilesMetadata(self, github_files_metadata):
        files_metadata = []
        for file in github_files_metadata:
            file_metadata = CommitFilesMetadata(file.filename, file.status,
                                                file.additions, file.deletions)
            files_metadata.append(file_metadata)
        return files_metadata

    def _getPatchStats(self, commit_stats):
        return CommitStats(commit_stats.additions, commit_stats.deletions,
                           commit_stats.total)

    def fetchCommitData(self, commit_hash=None):
        """Args:
        commit_hash:

        Returns:
        """
        if not commit_hash:
            commit_hash = self.commit_hash

        cache_file = CACHE_DIR + commit_hash + ".json"
        if self.use_cache and os.path.exists(cache_file):
            cache_content = lib.utils.get_file_contents(cache_file)
            return cache_content

        # Fetch relevant information from Github.
        github_repo = self.github.get_repo(
            f"{self.repo_owner}/{self.repo_name}")
        commit = github_repo.get_commit(commit_hash)
        commit_parents = commit.commit.parents
        parent_commit_hash = commit_hash
        if commit_parents:
            parent_commit_hash = commit_parents[0].sha

        # Fetch the list of all files in the previous "vulnerable" state.
        # Note: We use recursive=False (default) to only fetch the highest layer.
        git_tree = github_repo.get_git_tree(parent_commit_hash)
        # commit_url = commit.html_url commit_message = commit.commit.message affected_files = commit.files commit_parents = commit.commit.parents
        patched_files = self._ParsePatchPerFile(commit.files)

        commit_stats = self._getPatchStats(commit.stats)
        files_metadata = self._getFilesMetadata(commit.files)

        commit_date = int((commit.commit.committer.date -
                           datetime.datetime(1970, 1, 1)).total_seconds())
        commit_metadata = CommitMetadata(
            parent_commit_hash,
            commit_date,
            commit.commit.message,
            commit_stats,
            files_metadata,
        )

        data = self._CreateData(git_tree.tree, patched_files, commit_metadata)

        json_content = jsonify(data)
        if self.use_cache:
            lib.utils.write_contents(cache_file, json_content)
        return json_content
