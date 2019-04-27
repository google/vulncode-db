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

import os
from lib.utils import manuallyReadAppConfig
if not 'MYSQL_CONNECTION_NAME' in os.environ:
    print('[~] Executed outside AppEngine context. Manually loading config.')
    manuallyReadAppConfig()

import sys
sys.path.append('third_party/')

from lib.vcs_management import getVcsHandler
import pandas as pd
pd.set_option('display.max_colwidth', -1)
from flask import Flask, request
from sqlalchemy import or_, select, outerjoin, join, func
from data.models import Nvd, Reference, Vulnerability, VulnerabilityGitCommits
from data.database import DEFAULT_DATABASE, init_app as init_db
import sqlparse
import time

from colorama import Fore, Back, Style
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import SqlLexer

app = Flask(__name__, static_url_path='', template_folder='templates')
# Load the Flask configuration parameters from a global config file.
app.config.from_object('cfg')
# Load SQLAlchemy
init_db(app)
db = DEFAULT_DATABASE.db
# Push one single global flask app context for usage.
ctx = app.app_context()
ctx.push()
# Used for Pandas.
CVE_DB_ENGINE = db.get_engine(app, 'cve')


def writeHighlighted(text, color=Fore.WHITE, crlf=False):
  highlighted = (Style.BRIGHT + color + '%s' + Style.RESET_ALL) % text
  if crlf:
    print(highlighted)
  else:
    sys.stdout.write(highlighted)


def _measure_exution_time(label):

  def decorator(func):

    def wrapper(*args, **kwargs):
      start = time.time()
      res = func(*args, **kwargs)
      end = time.time()

      sys.stdout.write('[{}] '.format(label))
      writeHighlighted('~{:.4f}s'.format(end - start), color=Fore.YELLOW)
      print(' elapsed '.format(label))
      return res

    return wrapper

  return decorator


def dumpQuery(query, display_columns=[]):
  """Small helper function to dump a SqlAlchemy SQL query + parameters.

  :param query:
  :return:
  """
  # Number of rows to display.
  num_rows = 5

  if hasattr(query, 'statement'):
    sql_query = str(
        query.statement.compile(
            dialect=None, compile_kwargs={'literal_binds': True}))
  else:
    sql_query = str(query)

  formatted_sql_query = sqlparse.format(
      sql_query, reindent=True, keyword_case='upper')
  highlighted_sql_query = highlight(formatted_sql_query, SqlLexer(),
                                    TerminalFormatter())
  print('Query:')
  print('-' * 15 + '\n%s' % highlighted_sql_query + '-' * 15)

  df = pd.read_sql(query.statement, CVE_DB_ENGINE)
  if len(display_columns) > 0:
    df = df[display_columns]

  print('Results: {}; showing first {}:'.format(df.shape[0], num_rows))
  print(df.head(num_rows))


def getNvdGithubPatchCandidates():
  """Fetches concrete github.com commit links from the Nvd database.

  :return:
  """

  patch_regex = 'github\.com/([^/]+)/([^/]+)/commit/([^/]+)'

  sub_query = db.session.query(func.min(Reference.id)).filter(
      Reference.link.op('regexp')(patch_regex)).group_by(Reference.nvd_json_id)
  github_commit_candidates = db.session.query(Nvd, Reference.link, Vulnerability).select_from(
          join(Nvd, Reference).outerjoin(Vulnerability)).filter(Reference.id.in_(sub_query)).with_labels()

  return github_commit_candidates


def nvdToVcdb(nvd, commit_link):
  vcs_handler = getVcsHandler(app, commit_link)
  if not vcs_handler:
    print("Can't parse Vcs link: {}".format(commit_link))
    #print(vars(nvd))
    return None

  vulnerability = Vulnerability(
      cve_id=nvd.cve_id,
      commits=[
          VulnerabilityGitCommits(
              commit_link=commit_link,
              commit_hash=vcs_handler.commit_hash,
              repo_name=vcs_handler.repo_name,
              repo_owner=vcs_handler.repo_owner,
              repo_url=vcs_handler.repo_url)
      ],
      comment='',
  )
  return vulnerability


@_measure_exution_time('storeOrUpdateVcdbEntries')
def storeOrUpdateVcdbEntries(github_commit_candidates):
  """Fetches or creates VCDB

  :param github_commit_candidates:
  :return:
  """
  stats = {'created': 0, 'updated': 0, 'idle': 0, 'skipped': 0}

  for nvd_candidate in github_commit_candidates:
    nvd = nvd_candidate.Nvd
    commit_link = nvd_candidate.link
    existing_vcdb_vulnerability = nvd_candidate.Vulnerability

    vulnerability_suggestion = nvdToVcdb(nvd, commit_link)
    if not vulnerability_suggestion:
      print('[-] Invalid data detected for cve_id: {}'.format(nvd.cve_id))
      stats['skipped'] += 1
      continue

    if existing_vcdb_vulnerability:
      # Check if the entry has changed.
      has_changed = False
      if existing_vcdb_vulnerability.cve_id != vulnerability_suggestion.cve_id:
        print('{} != {}'.format(existing_vcdb_vulnerability.cve_id,
                                vulnerability_suggestion.cve_id))
        raise Exception('Incorrect vulnerability cve_id!')

      if (existing_vcdb_vulnerability.master_commit.repo_owner !=
          vulnerability_suggestion.master_commit.repo_owner):
        has_changed = True

      if (existing_vcdb_vulnerability.master_commit.commit_link !=
          vulnerability_suggestion.master_commit.commit_link):
        print('{} != {}'.format(
            existing_vcdb_vulnerability.master_commit.commit_link,
            vulnerability_suggestion.master_commit.commit_link))
        has_changed = True

      if has_changed:
        stats['updated'] += 1
        # TODO: Consider updating more attributes here.
        # Update only the commit_link and repo_owner for now.
        existing_vcdb_vulnerability.master_commit.commit_link = (
            vulnerability_suggestion.master_commit.commit_link)
        existing_vcdb_vulnerability.master_commit.repo_owner = (
            vulnerability_suggestion.master_commit.repo_owner)
        db.session.add(existing_vcdb_vulnerability)
        db.session.commit()
      else:
        stats['idle'] += 1
    else:
      # Add the new suggested Vcdb entry to the database.
      db.session.add(vulnerability_suggestion)
      db.session.commit()
      stats['created'] += 1
    sys.stdout.write('.')
    sys.stdout.flush()

  print('')
  return stats


def printStats(stats):
  sys.stdout.write('STATS: created(')
  writeHighlighted(stats['created'], Fore.GREEN)
  sys.stdout.write(') updated(')
  writeHighlighted(stats['updated'], Fore.GREEN)
  sys.stdout.write(') idle(')
  writeHighlighted(stats['idle'], Fore.CYAN)
  sys.stdout.write(') skipped(')
  writeHighlighted(stats['skipped'], Fore.RED)
  print(')')


@_measure_exution_time('Total')
def startCrawling():
  writeHighlighted(
      '1) Fetching entries from NVD with a direct github.com/*/commit/* commit link.',
      crlf=True)
  github_commit_candidates = getNvdGithubPatchCandidates()
  dumpQuery(github_commit_candidates, ['cve_nvd_jsons_id', 'cve_references_link'])

  writeHighlighted('2) Creating/updating existing Vcdb entries.', crlf=True)
  stats = storeOrUpdateVcdbEntries(github_commit_candidates)
  printStats(stats)

  print('Done')
  """- See how to best convert those entries into VCDB entries."""


if __name__ == '__main__':
  startCrawling()
