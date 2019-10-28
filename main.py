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
import logging
from logging.handlers import RotatingFileHandler

import alembic.script
import alembic.runtime.environment
from lib.utils import manually_read_app_config

if "MYSQL_CONNECTION_NAME" not in os.environ:
    print("[~] Executed outside AppEngine context. Manually loading config.")
    manually_read_app_config()

import cfg
from data.database import DEFAULT_DATABASE
from lib.app_factory import create_app

app = create_app()
db = DEFAULT_DATABASE.db


def check_db_state():
    with app.app_context():
        config = app.extensions["migrate"].migrate.get_config()
        script = alembic.script.ScriptDirectory.from_config(config)

        heads = script.get_revisions(script.get_heads())
        head_revs = frozenset(rev.revision for rev in heads)

        def check(rev, context):
            db_revs = frozenset(rev.revision
                                for rev in script.get_all_current(rev))
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

        with alembic.runtime.environment.EnvironmentContext(config,
                                                            script,
                                                            fn=check):
            script.run_env()


def main():
    if not cfg.IS_PROD:
        check_db_state()

    root_dir = os.path.dirname(os.path.realpath(__file__))
    error_file = os.path.join(root_dir, "error.log")

    handler = RotatingFileHandler(error_file, maxBytes=100000, backupCount=1)
    handler.setLevel(logging.WARNING)

    # app.logger = logging.getLogger('tdm')
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
    print(f"[+] Listening on: {use_protocol}://{use_host}:{use_port}")
    app.run(host=use_host, port=use_port, ssl_context=ssl_context, debug=True)


if __name__ == "__main__":
    main()
