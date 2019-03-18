#!/usr/bin/python
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

import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import traceback

from flask import Flask, request, Blueprint

from lib.vcs_management import getVcsHandler
from lib.utils import createJsonResponse

DEBUG = True

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__, static_url_path='', template_folder='templates')
bp = Blueprint('git', 'git')


@bp.route('/api/git')
def api_git():
  commit_hash = request.args.get('commit_hash', 0, type=str)
  item_hash = request.args.get('item_hash', 0, type=str)

  commit_link = request.args.get('commit_link', '', type=str)
  repo_url = request.args.get('repo_url', '', type=str)

  if 'github.com' in commit_link:
    resource_url = commit_link
  else:
    resource_url = repo_url if repo_url else commit_link

  vcs_handler = getVcsHandler(app, resource_url)
  if not vcs_handler:
    return createJsonResponse('Please provide a valid resource URL.', 400)

  try:
    # Return a specific file's content if requested instead.
    if item_hash:
      content = vcs_handler.getFileContent(item_hash)
      logging.info('Retrieved %s: %d bytes', item_hash, len(content))
      return content
    return vcs_handler.fetchCommitData(commit_hash)
  except Exception as e:
    if DEBUG:
      return createJsonResponse(str(e), 400, tb=traceback.format_exc())
    else:
      return createJsonResponse(str(e), 400)


app.register_blueprint(bp)

if __name__ == '__main__':
  root_dir = os.path.dirname(os.path.realpath(__file__))
  error_file = os.path.join(root_dir, 'vcs_error.log')

  handler = RotatingFileHandler(error_file, maxBytes=100000, backupCount=1)
  handler.setLevel(logging.WARNING)
  app.logger.addHandler(handler)
  app.logger.addHandler(logging.StreamHandler(stream=sys.stdout))
  if DEBUG:
    app.logger.setLevel(logging.DEBUG)
  else:
    app.logger.setLevel(logging.INFO)

  cert_dir = os.path.join(root_dir, 'cert')
  cert_file = os.path.join(cert_dir, 'cert.pem')
  key_file = os.path.join(cert_dir, 'key.pem')
  app.run(
      host='0.0.0.0', port=8080, ssl_context=(cert_file, key_file), debug=False)
