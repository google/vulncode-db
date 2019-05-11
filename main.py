#!/usr/bin/env python
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
import logging
from logging.handlers import RotatingFileHandler
import sys

from flask import (
    Flask,
    send_from_directory,
    render_template,
    request,
    url_for,
    redirect,
)
from flask_wtf.csrf import CSRFProtect
from flask_debugtoolbar import DebugToolbarExtension

import alembic.script
import alembic.runtime.environment
from flask_bootstrap import Bootstrap

from lib.utils import manually_read_app_config

if not "MYSQL_CONNECTION_NAME" in os.environ:
    print("[~] Executed outside AppEngine context. Manually loading config.")
    manually_read_app_config()
from app.auth import is_admin
from app.auth import bp as auth_bp
from app.api import bp as api_bp
from app.vuln import bp as vuln_bp
from app.vcs_proxy import bp as vcs_proxy_bp
from app.vulnerability import VulncodeDB
import cfg
from data.database import DEFAULT_DATABASE, init_app as init_db

app = Flask(__name__, static_url_path="", template_folder="templates")
app.register_blueprint(auth_bp)
app.register_blueprint(api_bp)
app.register_blueprint(vuln_bp)
app.register_blueprint(vcs_proxy_bp)

# Load the Flask configuration parameters from a global config file.
app.config.from_object("cfg")

# We use flask_wtf and WTForm with bootstrap for quick form rendering.
# Note: no JS/CSS or other resources are used from this package though.
Bootstrap(app)

# setup CSRF
csrf = CSRFProtect()
csrf.init_app(app)

# Load SQLAlchemy
init_db(app)
db = DEFAULT_DATABASE.db
# ------------------------------------------------
if not cfg.IS_PROD:
    # Activate a port of the django-debug-toolbar for Flask applications.
    # Shows executed queries + their execution time, allows profiling and more.
    # See: https://flask-debugtoolbar.readthedocs.io/en/latest/
    DebugToolbarExtension(app)


@app.before_request
def maintenance_check():
    if not cfg.MAINTENANCE_MODE:
        return
    allowed_prefixes = ["/about", "/static", "/auth"]
    for prefix in allowed_prefixes:
        if request.path.startswith(prefix):
            return
    if is_admin():
        return
    if request.path != url_for("maintenance"):
        return redirect(url_for("maintenance"))


# Static files
# TODO: Replace with nginx/apache for higher efficiency.
@app.route("/static/<path:path>")
def serve_static(path):
    return send_from_directory("static", path)


# ------------------------------------------------


@app.route("/")
def serve_index():
    vcdb = VulncodeDB()
    return render_template("index.html", vcdb=vcdb)


@app.route("/maintenance")
def maintenance():
    return render_template("maintenance.html")


@app.route("/list_entries")
def list_entries():
    vcdb = VulncodeDB()
    return render_template("list_vuln_entries.html", vcdb=vcdb)


def check_db_state():
    with app.app_context():
        config = app.extensions["migrate"].migrate.get_config()
        script = alembic.script.ScriptDirectory.from_config(config)

        heads = script.get_revisions(script.get_heads())
        head_revs = frozenset(rev.revision for rev in heads)

        def check(rev, context):
            db_revs = frozenset(
                rev.revision for rev in script.get_all_current(rev))
            if db_revs ^ head_revs:
                config.print_stdout(
                    "Current revision(s) for %s %s do not match the heads %s\n.Run ./manage.sh db upgrade.",
                    alembic.util.obfuscate_url_pw(
                        context.connection.engine.url),
                    tuple(db_revs),
                    tuple(head_revs),
                )
                sys.exit(1)
            return []

        with alembic.runtime.environment.EnvironmentContext(
                config, script, fn=check):
            script.run_env()


def main():
    if not cfg.IS_PROD:
        check_db_state()

    root_dir = os.path.dirname(os.path.realpath(__file__))
    error_file = os.path.join(root_dir, "error.log")

    handler = RotatingFileHandler(error_file, maxBytes=100000, backupCount=1)
    # logging.basicConfig()
    # logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    handler.setLevel(logging.WARNING)
    app.logger.addHandler(handler)
    app.logger.addHandler(logging.StreamHandler(stream=sys.stdout))
    if cfg.DEBUG:
        app.logger.setLevel(logging.DEBUG)
        logging.getLogger("root").setLevel(logging.DEBUG)
    else:
        app.logger.setLevel(logging.INFO)

    # cert_dir = os.path.join(root_dir, 'cert')
    # cert_file = os.path.join(cert_dir, 'cert.pem')
    # key_file = os.path.join(cert_dir, 'key.pem')

    ssl_context = None
    # Uncomment line below if you prefer using SSL here.
    # ssl_context = (cert_file, key_file)
    use_host = "0.0.0.0"
    use_port = 8080
    use_protocol = "https" if ssl_context else "http"
    print("[+] Listening on: {}://{}:{}".format(use_protocol, use_host,
                                                use_port))
    app.run(host=use_host, port=use_port, ssl_context=ssl_context, debug=True)


if __name__ == "__main__":
    main()
