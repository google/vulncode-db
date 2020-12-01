#!/usr/bin/env python3
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
import sys

import pandas as pd
import sqlparse

from colorama import Fore, Style
from flask import Flask
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import SqlLexer
from sqlalchemy import and_, join, func

from data.database import DEFAULT_DATABASE, init_app as init_db
from data.models import (
    Nvd,
    Vulnerability,
    VulnerabilityGitCommits,
    Cpe,
    Product,
    Reference,
    VulnerabilityState,
)
from lib.utils import manually_read_app_config
from lib.utils import measure_execution_time
from lib.vcs_management import get_vcs_handler

if "MYSQL_CONNECTION_NAME" not in os.environ:
    print("[~] Executed outside AppEngine context. Manually loading config.")
    # updates os.environ
    manually_read_app_config()

pd.set_option("display.max_colwidth", -1)

app = Flask(__name__, static_url_path="", template_folder="templates")
# Load the Flask configuration parameters from a global config file.
app.config.from_object("cfg")
# Load SQLAlchemy
init_db(app)
db = DEFAULT_DATABASE.db
# Push one single global flask app context for usage.
ctx = app.app_context()
ctx.push()
# Used for Pandas.
CVE_DB_ENGINE = db.get_engine(app)


def write_highlighted(text, color=Fore.WHITE, crlf=True):
    highlighted = (Style.BRIGHT + color + "%s" + Style.RESET_ALL) % text
    if crlf:
        print(highlighted)
    else:
        sys.stdout.write(highlighted)


def dump_query(query, filter_columns=None):
    """
    Small helper function to dump a SqlAlchemy SQL query + parameters.

    :param query:
    :param filter_columns:
    :return:
    """
    # Number of rows to display.
    num_rows = 5

    if hasattr(query, "statement"):
        sql_query = str(
            query.statement.compile(
                dialect=None, compile_kwargs={"literal_binds": True}
            )
        )
    else:
        sql_query = str(query)

    formatted_sql_query = sqlparse.format(
        sql_query, reindent=True, keyword_case="upper"
    )
    highlighted_sql_query = highlight(
        formatted_sql_query, SqlLexer(), TerminalFormatter()
    )
    print("Query:")
    print(f"{'-' * 15}\n{highlighted_sql_query}{'-' * 15}")

    data_frame = pd.read_sql(query.statement, CVE_DB_ENGINE)
    if filter_columns:
        data_frame = data_frame[filter_columns]

    print(f"Results: {data_frame.shape[0]}; showing first {num_rows}:")
    print(data_frame.head(num_rows))


def get_nvd_github_patch_candidates():
    """
    Fetches concrete github.com commit links from the Nvd database.

    :return:
    """
    patch_regex = r"github\.com/([^/]+)/([^/]+)/commit/([^/]+)"

    sub_query = (
        db.session.query(func.min(Reference.id))
        .filter(Reference.link.op("regexp")(patch_regex))
        .group_by(Reference.nvd_json_id)
    )
    github_commit_candidates = (
        db.session.query(Nvd.cve_id, Reference.link, Vulnerability)
        .select_from(
            join(Nvd, Reference).outerjoin(
                Vulnerability, Nvd.cve_id == Vulnerability.cve_id
            )
        )
        .filter(Reference.id.in_(sub_query))
        .with_labels()
    )

    return github_commit_candidates


def create_vcdb_entry(cve_id, commit_link=None):
    vuln_commits = []
    if commit_link:
        vcs_handler = get_vcs_handler(app, commit_link)
        if not vcs_handler:
            print(f"Can't parse Vcs link: {commit_link}")
            return None
        vuln_commit = VulnerabilityGitCommits(
            commit_link=commit_link,
            commit_hash=vcs_handler.commit_hash,
            repo_name=vcs_handler.repo_name,
            repo_owner=vcs_handler.repo_owner,
            repo_url=vcs_handler.repo_url,
        )
        vuln_commits.append(vuln_commit)

    vulnerability = Vulnerability(
        cve_id=cve_id,
        commits=vuln_commits,
        comment="",
        version=0,
        state=VulnerabilityState.PUBLISHED,
    )
    return vulnerability


@measure_execution_time("store_or_update_vcdb_entries")
def store_or_update_vcdb_entries(github_commit_candidates):
    """
    Fetches or creates VCDB.

    :param github_commit_candidates:
    :return:
    """
    stats = {"created": 0, "updated": 0, "idle": 0, "skipped": 0}

    for nvd_candidate in github_commit_candidates:
        nvd_cve_id = nvd_candidate.cve_id
        existing_vcdb_vulnerability = nvd_candidate.Vulnerability
        commit_link = None
        if hasattr(nvd_candidate, "link"):
            commit_link = nvd_candidate.link

        vulnerability_suggestion = create_vcdb_entry(nvd_cve_id, commit_link)
        if not vulnerability_suggestion:
            print(f"[-] Invalid data detected for cve_id: {nvd_cve_id}")
            stats["skipped"] += 1
            continue

        if existing_vcdb_vulnerability:
            # Check if the entry has changed.
            has_changed = False
            if existing_vcdb_vulnerability.cve_id != vulnerability_suggestion.cve_id:
                print(
                    "{} != {}".format(
                        existing_vcdb_vulnerability.cve_id,
                        vulnerability_suggestion.cve_id,
                    )
                )
                raise Exception("Incorrect vulnerability cve_id!")

            if existing_vcdb_vulnerability.master_commit:
                if (
                    existing_vcdb_vulnerability.master_commit.repo_owner
                    != vulnerability_suggestion.master_commit.repo_owner
                ):
                    has_changed = True

                if (
                    existing_vcdb_vulnerability.master_commit.commit_link
                    != vulnerability_suggestion.master_commit.commit_link
                ):
                    print(
                        "{} != {}".format(
                            existing_vcdb_vulnerability.master_commit.commit_link,
                            vulnerability_suggestion.master_commit.commit_link,
                        )
                    )
                    has_changed = True

            if has_changed:
                stats["updated"] += 1
                # TODO: Consider updating more attributes here.
                # Update only the commit_link and repo_owner for now.
                existing_vcdb_vulnerability.master_commit.commit_link = (
                    vulnerability_suggestion.master_commit.commit_link
                )
                existing_vcdb_vulnerability.master_commit.repo_owner = (
                    vulnerability_suggestion.master_commit.repo_owner
                )
                db.session.add(existing_vcdb_vulnerability)
            else:
                stats["idle"] += 1
        else:
            # Add the new suggested Vcdb entry to the database.
            db.session.add(vulnerability_suggestion)
            stats["created"] += 1
        sys.stdout.write(".")
        sys.stdout.flush()
    db.session.commit()

    print("")
    return stats


def print_stats(stats):
    sys.stdout.write("STATS: created(")
    write_highlighted(stats["created"], Fore.GREEN, False)
    sys.stdout.write(") updated(")
    write_highlighted(stats["updated"], Fore.GREEN, False)
    sys.stdout.write(") idle(")
    write_highlighted(stats["idle"], Fore.CYAN, False)
    sys.stdout.write(") skipped(")
    write_highlighted(stats["skipped"], Fore.RED, False)
    print(")")


def update_oss_table():
    # Fetch all distinct vendor, product tuples from the main table.
    unique_products = db.session.query(Cpe.vendor, Cpe.product)
    unique_products = unique_products.select_from(
        join(Nvd, Cpe).outerjoin(Vulnerability, Vulnerability.cve_id == Nvd.cve_id)
    )
    unique_products = unique_products.filter(Vulnerability.cve_id.isnot(None))
    unique_products = unique_products.distinct(Cpe.vendor, Cpe.product)
    # Fetch only entries which are not already contained in OpenSourceProducts.
    unique_products = unique_products.outerjoin(
        Product, and_(Cpe.vendor == Product.vendor, Cpe.product == Product.product)
    )
    unique_products = unique_products.filter(Product.vendor.is_(None))
    dump_query(unique_products)

    # We don't do any updates for now.
    created = 0
    for entry in unique_products:
        new_entry = Product(
            vendor=entry.vendor, product=entry.product, is_open_source=True
        )
        db.session.add(new_entry)
        sys.stdout.write(".")
        sys.stdout.flush()
        created += 1
    db.session.commit()
    print("")
    sys.stdout.write("created(")
    write_highlighted(created, Fore.GREEN, False)
    sys.stdout.write(")")


def create_oss_entries():
    nvd_entries = db.session.query(Nvd.cve_id, Vulnerability)
    nvd_entries = nvd_entries.select_from(
        join(Nvd, Cpe).outerjoin(Vulnerability, Nvd.cve_id == Vulnerability.cve_id)
    ).with_labels()
    nvd_entries = nvd_entries.filter(Vulnerability.cve_id.is_(None))
    # nvd_entries = nvd_entries.options(default_nvd_view_options)
    nvd_entries = nvd_entries.join(
        Product,
        and_(
            Cpe.vendor == Product.vendor,
            Cpe.product == Product.product,
            Product.is_open_source == True,  # pylint: disable=singleton-comparison
        ),
    )
    nvd_entries = nvd_entries.distinct(Nvd.cve_id)
    return nvd_entries


@measure_execution_time("Total")
def start_crawling():
    """See how to best convert those entries into VCDB entries."""
    write_highlighted(
        "1) Fetching entries from NVD with a direct github.com/*/commit/* commit link."
    )
    github_commit_candidates = get_nvd_github_patch_candidates()
    # update_oss_table()
    # exit()
    # write_highlighted("Fetching all entries that affect open source software."
    #                  )
    # github_commit_candidates = create_oss_entries()
    dump_query(github_commit_candidates)

    write_highlighted("2) Creating/updating existing Vcdb entries.")
    stats = store_or_update_vcdb_entries(github_commit_candidates)
    print_stats(stats)

    print("Done")


if __name__ == "__main__":
    start_crawling()
