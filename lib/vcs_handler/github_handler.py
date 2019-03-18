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

import io
import json
import logging
import os
import re

try:
  from urlparse import urlparse
except ImportError:
  from urllib.parse import urlparse

from github import Github
from unidiff import PatchSet

from app.exceptions import InvalidIdentifierException
from lib.vcs_handler.vcs_handler import VcsHandler, HASH_PLACEHOLDER
import lib.utils

CACHE_DIR = 'cache/'
"""def get_github_archive_link(owner, repo, hash):

  link =
  'https://github.com/{owner}/{repo}/archive/{hash}.zip'.format(owner=owner,
  repo=repo, hash=hash)
  return link
"""


class GithubHandler(VcsHandler):
  use_cache = True

  def __init__(self, app, resource_url):
    """Initializes the questionnaire object."""
    super(GithubHandler, self).__init__(app, resource_url)
    self.cache = None

    self.github = Github()
    self.parseResourceURL(resource_url)

  def parseResourceURL(self, resource_url):
    if not resource_url:
      raise InvalidIdentifierException('Please provide a Github commit link.')
    url_data = urlparse(resource_url)
    git_path = url_data.path
    matches = re.match(r'/([^/]+)/([^/]+)/commit/([^/]+)/?$', git_path)
    if not url_data.hostname or 'github.com' not in url_data.hostname or not matches:
      raise InvalidIdentifierException(
          'Please provide a valid (https://github.com/{owner}/{repo}/commit/{hash}) commit link.'
      )
    self.repo_owner, self.repo_name, self.commit_hash = matches.groups()
    self.commit_link = resource_url

  def _ParsePatchPerFile(self, files):
    patched_files = {}
    # Process all patches provided by Github and save them in a new per file per line representation.
    for patched_file in files:
      patched_files[patched_file.filename] = []

      # patch_str = io.StringIO()
      # patch_str.write('--- a\n+++ b\n')
      # patch_str.write(str(patched_file.patch))
      # patch_str.seek(0)
      # logging.debug('Parsing diff\n%s', patch_str.getvalue())
      #
      # patch = PatchSet(patch_str, encoding=None)
      # TODO: Migrate this to io.StringIO().
      patch_str = '--- a\n+++ b\n' + str(patched_file.patch)
      logging.debug('Parsing diff\n%s', patch_str)
      patch = PatchSet(patch_str, encoding='utf-8')

      for hunk in patch[0]:
        for line in hunk:
          if line.is_context:
            continue
          patched_files[patched_file.filename].append(vars(line))
    return patched_files

  def getFileProviderUrl(self):
    return (
        'https://api.github.com/repos/{owner}/{repo}/git/blobs/{HASH_PLACEHOLDER}'
        .format(
            owner=self.repo_owner,
            repo=self.repo_name,
            HASH_PLACEHOLDER=HASH_PLACEHOLDER))

  def getFileUrl(self):
    return ('https://github.com/{owner}/{repo}/blob/{commit_hash}/'.format(
        owner=self.repo_owner,
        repo=self.repo_name,
        commit_hash=self.commit_hash))

  def fetchCommitData(self, commit_hash=None):
    """Args:

      commit_hash:

    Returns:

    """
    if not commit_hash:
      commit_hash = self.commit_hash

    cache_file = CACHE_DIR + commit_hash + '.json'
    if self.use_cache and os.path.exists(cache_file):
      cache_content = lib.utils.get_file_contents(cache_file)
      return cache_content

    # Fetch relevant information from Github.
    github_repo = self.github.get_repo('{owner}/{repo}'.format(
        owner=self.repo_owner, repo=self.repo_name))
    commit = github_repo.get_commit(commit_hash)
    commit_parents = commit.commit.parents
    parent_commit_hash = commit_hash
    if commit_parents:
      parent_commit_hash = commit_parents[0].sha

    # Fetch the list of all files in the previous "vulnerable" state.
    git_tree = github_repo.get_git_tree(parent_commit_hash, True)
    """commit_url = commit.html_url commit_message = commit.commit.message affected_files = commit.files commit_parents = commit.commit.parents"""
    patched_files = self._ParsePatchPerFile(commit.files)
    editor_data = self._CreateData(self.repo_name, commit_hash, patched_files,
                                   git_tree.tree)

    data = {
        'file_provider_url': self.getFileProviderUrl(),
        'files': editor_data
    }

    json_content = json.dumps(data)
    if self.use_cache:
      lib.utils.write_contents(cache_file, json_content)
    return json_content
