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

HASH_PLACEHOLDER = '--ITEM_HASH--'


class VcsHandler(object):

  def __init__(self, app, resource_url):
    self.app = app
    self.resource_url = resource_url

    self.commit_link = None
    self.commit_hash = None

    self.repo_owner = None
    self.repo_name = None
    self.repo_url = None

  def _logError(self, error, *args, **kwargs):
    if self.app:
      return self.app.logger.error(error, *args, **kwargs)

  def getFileContent(self, relative_repo_path):
    pass

  def fetchCommitData(self, commit_hash):
    pass

  def parseResourceURL(self, commit_link):
    pass

  def getFileProviderUrl(self):
    pass

  def _CreateData(self, repo_name, commit_hash, patched_files, git_tree):
    # Create a JStree structure.
    root = {}
    root['core'] = {}
    root['core']['data'] = []
    root_node = {
        'text': repo_name,
        'data': {
            'id': 0,
            'hash': commit_hash
        },
        'state': {
            'opened': True
        },
        'children': []
    }
    root['core']['data'].append(root_node)

    # Attention: we need to start from 1 as the root id is already 0!
    current_node_id = {'counter': 1}

    def append(current_root_node, items, last_depth=1):
      while len(items) > 0:
        current_depth = len(items[0].path.split('/'))
        if current_depth < last_depth:
          return
        tree_item = items.pop(0)

        node = {}
        node['text'] = os.path.basename(tree_item.path)
        node['data'] = {}
        # Using a counter workaround here as python 2.x does not support the "nonlocal" keyword.
        node['data']['id'] = current_node_id['counter']
        current_node_id['counter'] += 1
        node['data']['hash'] = tree_item.sha
        # Append patch data if available.
        if tree_item.path in patched_files:
          node['data']['patch'] = patched_files[tree_item.path]
        if tree_item.type == 'blob':
          node['icon'] = 'jstree-file'
          current_root_node['children'].append(node)
        else:
          node['children'] = []
          append(node, items, last_depth + 1)
          current_root_node['children'].append(node)

    items_copy = [a for a in git_tree]
    append(root_node, items_copy)

    def sortme(node):
      node['children'].sort(key=lambda x: ('children' not in x))
      for i in node['children']:
        if 'children' in i:
          sortme(i)

    sortme(root_node)
    return root
