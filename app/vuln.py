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
import json
import logging

try:
  import urllib2
except ImportError:
  import urllib.request as urllib2

from flask import Blueprint, redirect, flash, request, render_template, abort, url_for, Response, send_file

from app import flashError
from app.auth import admin_required
from app.exceptions import InvalidIdentifierException
from app.vulnerability import VulnerabilityDetails
import cfg
from data.models import RepositoryFilesSchema
from data.forms import VulnerabilityDeleteForm, VulnerabilityDetailsForm
from data.database import DEFAULT_DATABASE
from lib.vcs_management import get_vcs_handler
from lib.utils import create_json_response

bp = Blueprint('vuln', __name__, url_prefix='/')
db = DEFAULT_DATABASE


def view_vuln(vuln_id, use_template):
  try:
    vulnerability_details = VulnerabilityDetails(vuln_id)
    vulnerability_details.validate()
  except InvalidIdentifierException as err:
    return flashError(str(err), 'serve_index')
  return render_template(
      use_template, cfg=cfg, vulnerability_details=vulnerability_details)


@bp.route('/vuln', methods=['POST'])
def vuln_view_post():
  return view_vuln(None, 'vuln_view_overview.html')


def _get_vulnerability_details(vuln_id):
  try:
    vulnerability_details = VulnerabilityDetails(vuln_id)
    vulnerability_details.validate()
    # Drop everything else.
    if not vulnerability_details.vulnerability_view:
      abort(404)
    return vulnerability_details
  except InvalidIdentifierException:
    abort(404)


# Create a catch all route for vulnerability identifiers.
@bp.route('/<vuln_id>')
def vuln_view(vuln_id=None):
  vulnerability_details = _get_vulnerability_details(vuln_id)
  vuln_view = vulnerability_details.vulnerability_view
  use_template = 'vuln_view_details.html'
  if vuln_view.annotated:
    use_template = 'vuln_view_overview.html'
  return render_template(
      use_template, cfg=cfg, vulnerability_details=vulnerability_details)


@bp.route('/<vuln_id>/details')
def vuln_view_details(vuln_id):
  return view_vuln(vuln_id, 'vuln_view_details.html')


@bp.route('/<vuln_id>/editor')
def vuln_editor(vuln_id):
  return view_vuln(vuln_id, 'vuln_edit.html')


@bp.route('/<vuln_id>/tree')
def vuln_file_tree(vuln_id):
  vulnerability_details = _get_vulnerability_details(vuln_id)
  vuln_view = vulnerability_details.vulnerability_view
  master_commit = vuln_view.master_commit

  status_code = 200
  content_type = 'text/json'
  response_msg = master_commit.tree_cache
  if not response_msg:
    try:
      vulnerability_details.fetch_tree_cache(skip_errors=False, max_timeout=10)
      response_msg = master_commit.tree_cache
    except urllib2.HTTPError as err:
      status_code = err.code
      response_msg = ''.join(['VCS proxy is unreachable (it might be down).',
                              '\r\nHTTPError\r\n',
                              err.read()])
      content_type = 'text/plain'
    except urllib2.URLError as err:
      status_code = 400
      response_msg = ''.join(['VCS proxy is unreachable (it might be down).',
                              '\r\nURLError\r\n',
                              err.reason])
      content_type = 'text/plain'
    except Exception as err:
      status_code = 400
      content_type = 'text/plain'
      response_msg = 'VCS proxy is unreachable (it might be down).'

  return Response(
      response=response_msg, status=status_code, content_type=content_type)


@bp.route('/<vuln_id>/annotation_data')
def annotation_data(vuln_id):
  vulnerability_details = _get_vulnerability_details(vuln_id)
  vulnerability_details.validate()
  vuln_view = vulnerability_details.vulnerability_view
  master_commit = vuln_view.master_commit
  if not master_commit:
    logging.error('Vuln (id: {:d}) has no linked Git commits!'.format(
        vuln_view.id))
    return create_json_response('Entry has no linked Git link!', 404)

  master_commit = vulnerability_details.getMasterCommit()
  files_schema = RepositoryFilesSchema(many=True)
  return files_schema.jsonify(master_commit.repository_files)


@bp.route('/<vuln_id>/file_provider')
def file_provider(vuln_id):
  vulnerability_details = _get_vulnerability_details(vuln_id)
  vulnerability_details.validate()

  item_hash = request.args.get('item_hash', 0, type=str)
  item_path = request.args.get('item_path', None, type=str)

  proxy_target = cfg.GCE_VCS_PROXY_URL + url_for(
      'vcs_proxy.main_api',
      repo_url=vulnerability_details.repo_url,
      item_path=item_path,
      item_hash=item_hash)[1:]

  try:
    result = urllib2.urlopen(proxy_target)
  except urllib2.HTTPError as err:
    return Response(response=err.read(), status=err.code, content_type='text/plain')
  return send_file(result, mimetype='application/octet-stream')


@bp.route('/<vuln_id>/embed')
def embed(vuln_id):
  try:
    section_id = int(request.args.get('sid', -1))
    start_line = int(request.args.get('start_line', 1))
    end_line = int(request.args.get('end_line', -1))
    vulnerability_details = VulnerabilityDetails(vuln_id)
    vulnerability_details.validate()
    vuln_view = vulnerability_details.vulnerability_view
    if not vuln_view:
      return bp.make_response(('No vulnerability found', 404))
    if not vuln_view.master_commit:
      return bp.make_response(
          ('Vuln (id: {:d}) has no linked Git commits!'.format(vuln_view.id),
           404))

    master_commit = vulnerability_details.getMasterCommit()
    files_schema = RepositoryFilesSchema(many=True)
    # Hack to quickly retrieve the full data.
    custom_data = json.loads(
        files_schema.jsonify(master_commit.repository_files).data)
    settings = {
        'section_id': section_id,
        'startLine': start_line,
        'endLine': end_line,
        'entry_data': custom_data
    }
    return render_template(
        'embedded.html',
        cfg=cfg,
        vulnerability_details=vulnerability_details,
        embed_settings=settings)
  except (ValueError, InvalidIdentifierException):
    abort(404)


@bp.route('/<vuln_id>/create', methods=['GET', 'POST'])
@bp.route('/create', methods=['GET', 'POST'])
@admin_required()
def create_vuln(vuln_id=None):
  return _create_vuln_internal(vuln_id)


def _create_vuln_internal(vuln_id=None):
  try:
    vulnerability_details = VulnerabilityDetails(vuln_id)
    vulnerability = vulnerability_details.get_or_create_vulnerability()
  except InvalidIdentifierException as err:
    return flashError(str(err), 'serve_index')

  if vulnerability.id:
    logging.debug('Preexisting vulnerability entry found: %s', vulnerability.id)
    delete_form = VulnerabilityDeleteForm()
    if delete_form.validate_on_submit():
      db.session.delete(vulnerability)
      # Remove the entry.
      db.session.commit()
      flash('The entry was deleted.', 'success')
      return redirect('/')

  form = VulnerabilityDetailsForm(obj=vulnerability)
  commit = form.data['commits'][0]
  if not commit['repo_name']:
    logging.info('Empty repository name. %r', commit)
    repo_url = commit['repo_url']
    vcs_handler = get_vcs_handler(None, repo_url)
    if vcs_handler:
      logging.info('Found name. %r', vcs_handler.repo_name)
      form.commits[0].repo_name.process_data(vcs_handler.repo_name)

  if form.validate_on_submit():
    try:
      form.populate_obj(vulnerability)
      db.session.add(vulnerability)
      db.session.commit()
      logging.debug('Successfully created/updated entry: %s', vulnerability.id)
      flash('Successfully created/updated entry.', 'success')
      return redirect(url_for('vuln.vuln_view', vuln_id=vulnerability.id))
    except InvalidIdentifierException as err:
      flashError(str(err))

  return render_template(
      'create_entry.html',
      cfg=cfg,
      vulnerability_details=vulnerability_details,
      form=form)
