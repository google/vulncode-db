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

HASH_PLACEHOLDER = "--ITEM_HASH--"
PATH_PLACEHOLDER = "--PATH_PLACE--"
VULN_ID_PLACEHOLDER = "--ID_PLACE--"


class CommitStats(object):
    def __init__(self, additions, deletions, total):
        self.additions = additions
        self.deletions = deletions
        self.total = total


class CommitFilesMetadata(object):
    def __init__(self, path, status, additions, deletions):
        self.path = path
        self.status = status
        self.additions = additions
        self.deletions = deletions


class CommitMetadata(object):
    def __init__(self, parent_commit_hash, date, message, stats,
                 files_metadata):
        self.parent_commit_hash = parent_commit_hash
        self.date = date
        self.message = message
        self.stats = stats
        self.files_metadata = files_metadata


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

    def getFileContent(self, item_hash, item_path=None):
        pass

    def fetchCommitData(self, commit_hash):
        pass

    def parseResourceURL(self, commit_link):
        pass

    def getFileProviderUrl(self):
        pass

    def getRefFileProviderUrl(self):
        pass

    def getFileUrl(self):
        pass

    def getTreeUrl(self):
        pass

    def _CreateData(self, git_tree, patched_files, commit_metadata):
        files = []

        commit_data = {
            "message": commit_metadata.message,
            "date": commit_metadata.date,
            "parent_hash": commit_metadata.parent_commit_hash,
            "stats": commit_metadata.stats.__dict__,
            "files": [f.__dict__ for f in commit_metadata.files_metadata],
        }

        for root_file in git_tree:
            file = {
                "path": root_file.path,
                "sha": root_file.sha,
                "type": root_file.type,
            }
            files.append(file)

        data = {
            "commit": commit_data,
            "patched_files": patched_files,
            "files": files
        }
        return data
