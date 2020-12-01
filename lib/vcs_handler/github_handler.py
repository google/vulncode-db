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

from flask import jsonify
from github import Github  # type: ignore
from unidiff import PatchSet  # type: ignore

import lib.utils

from app.exceptions import InvalidIdentifierException
from lib.vcs_handler.vcs_handler import (
    VcsHandler,
    HASH_PLACEHOLDER,
    PATH_PLACEHOLDER,
    CommitStats,
    CommitFilesMetadata,
    CommitMetadata,
)

CACHE_DIR = "cache/"
"""
def get_github_archive_link(owner, repo, hash):

  link =
  'https://github.com/{owner}/{repo}/archive/{hash}.zip'.format(owner=owner,
  repo=repo, hash=hash)
  return link
"""


class GithubHandler(VcsHandler):
    def __init__(self, app, resource_url=None):
        """Initializes the questionnaire object."""
        super().__init__(app, resource_url)
        # We're currently using DB caching for file tree data.
        self.use_cache = False

        use_token = None
        if app and "GITHUB_API_ACCESS_TOKEN" in app.config:
            use_token = app.config["GITHUB_API_ACCESS_TOKEN"]

        self.github = Github(login_or_token=use_token)
        if resource_url is not None:
            self.parse_resource_url(resource_url)

    def parse_resource_url(self, resource_url):
        if not resource_url:
            raise InvalidIdentifierException("Please provide a Github commit link.")
        url_data = urlparse(resource_url)
        git_path = url_data.path
        matches = re.match(r"/([^/]+)/([^/]+)/commit/([^/]+)/?$", git_path)
        if (
            not url_data.hostname
            or "github.com" not in url_data.hostname
            or not matches
        ):
            raise InvalidIdentifierException(
                "Please provide a valid "
                "(https://github.com/{owner}/{repo}/commit/{hash})"
                " commit link."
            )
        self.repo_owner, self.repo_name, self.commit_hash = matches.groups()
        self.repo_url = f"https://github.com/{self.repo_owner}/{self.repo_name}"
        self.commit_link = resource_url

    def parse_url_and_hash(self, repo_url, commit_hash):
        if not repo_url or not commit_hash:
            raise InvalidIdentifierException("Please provide a Github url and hash.")
        url_data = urlparse(repo_url)
        git_path = url_data.path
        matches = re.match(r"/([^/]+)/([^/]+)/?$", git_path)
        if (
            not url_data.hostname
            or "github.com" not in url_data.hostname
            or not matches
        ):
            raise InvalidIdentifierException(
                "Please provide a valid "
                "(https://github.com/{owner}/{repo})"
                " repository url."
            )
        if not re.match(r"[a-fA-F0-9]{5,}$", commit_hash):
            raise InvalidIdentifierException(
                "Please provide a valid " "git commit hash (min 5 characters)"
            )
        self.repo_owner, self.repo_name = matches.groups()
        self.repo_url = repo_url
        self.commit_hash = commit_hash
        self.commit_link = f"{repo_url}/commit/{commit_hash}"

    @staticmethod
    def _parse_patch_per_file(files):
        patched_files = {}
        # Process all patches provided by Github and save them in a new per
        # file per line representation.
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
            logging.debug("Parsing diff\n%s", patch_str.getvalue())
            patch = PatchSet(patch_str, encoding=None)

            for hunk in patch[0]:
                for line in hunk:
                    if line.is_context:
                        continue
                    patched_files[patched_file.filename]["deltas"].append(vars(line))

        return patched_files

    def get_file_provider_url(self):
        owner = self.repo_owner
        repo = self.repo_name
        return (
            f"https://api.github.com/repos/{owner}/{repo}/git/"
            + f"blobs/{HASH_PLACEHOLDER}"
        )

    def get_ref_file_provider_url(self):
        owner = self.repo_owner
        repo = self.repo_name
        return (
            f"https://api.github.com/repos/{owner}/{repo}/contents/"
            + f"{PATH_PLACEHOLDER}?ref={HASH_PLACEHOLDER}"
        )

    def get_file_url(self):
        owner = self.repo_owner
        repo = self.repo_name
        commit_hash = self.commit_hash
        return f"https://github.com/{owner}/{repo}/blob/{commit_hash}/"

    def get_tree_url(self):
        owner = self.repo_owner
        repo = self.repo_name
        commit_hash = self.commit_hash
        return f"https://github.com/{owner}/{repo}/tree/{commit_hash}/"

    @staticmethod
    def _get_files_metadata(github_files_metadata):
        files_metadata = []
        for file in github_files_metadata:
            file_metadata = CommitFilesMetadata(
                file.filename, file.status, file.additions, file.deletions
            )
            files_metadata.append(file_metadata)
        return files_metadata

    @staticmethod
    def _get_patch_stats(commit_stats):
        return CommitStats(
            commit_stats.additions, commit_stats.deletions, commit_stats.total
        )

    def fetch_commit_data(self, commit_hash=None):
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
        github_repo = self.github.get_repo(f"{self.repo_owner}/{self.repo_name}")
        commit = github_repo.get_commit(commit_hash)
        commit_parents = commit.commit.parents
        parent_commit_hash = commit_hash
        if commit_parents:
            parent_commit_hash = commit_parents[0].sha

        # Fetch the list of all files in the previous "vulnerable" state.
        # Note: We use recursive=False (default) to only fetch the highest
        # layer.
        git_tree = github_repo.get_git_tree(parent_commit_hash)
        # commit_url = commit.html_url
        commit_message = commit.commit.message
        commit_files = commit.files
        # commit_parents = commit.commit.parents
        patched_files = self._parse_patch_per_file(commit_files)

        commit_stats = self._get_patch_stats(commit.stats)
        files_metadata = self._get_files_metadata(commit_files)

        commit_date = int(
            (
                commit.commit.committer.date - datetime.datetime(1970, 1, 1)
            ).total_seconds()
        )
        commit_metadata = CommitMetadata(
            parent_commit_hash,
            commit_date,
            commit_message,
            commit_stats,
            files_metadata,
        )

        data = self._create_data(git_tree.tree, patched_files, commit_metadata)

        json_content = jsonify(data)
        if self.use_cache:
            lib.utils.write_contents(cache_file, json_content)
        return json_content
