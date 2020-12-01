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

import logging
import os
import socket
import sys
from logging.handlers import RotatingFileHandler

from flask import Flask, request, Blueprint

from lib.vcs_management import get_vcs_handler
from lib.utils import create_json_response


def manually_read_app_config():
    config = {}
    try:
        import yaml  # pylint: disable=import-outside-toplevel
    except ImportError:
        return None
    with open("vcs_proxy.yaml") as file:
        try:
            config = yaml.load(file, Loader=yaml.SafeLoader)
        except yaml.YAMLError as err:
            print(err)
    return config


vcs_config = manually_read_app_config()
if not vcs_config:
    vcs_config = {}

# Attention: Only enabled for local / qa debugging.
# This will enable pretty formatting of JSON and have other negative
# side-effects when being run in prod.
DEBUG = False
IS_PROD = False

if "PROD_HOSTNAME" in vcs_config:
    if vcs_config["PROD_HOSTNAME"] == socket.gethostname():
        IS_PROD = True

if not IS_PROD:
    print("[!] Running in dev mode!")
    DEBUG = True
else:
    print("[!] Running in prod mode!")

# This will lead to UnicodeEncodeError: 'ascii' codec can't encode [...] errors
# as it will try to log unicode results as str.
#  logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__, static_url_path="", template_folder="templates")
# Used to remove spaces from long JSON responses.
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = False
app.config["GITHUB_API_ACCESS_TOKEN"] = None

bp = Blueprint("vcs_proxy", "main_api")


# Note: This has to match the app/vcs_proxy.py blueprint.
@bp.route("/main_api")
def main_api():
    commit_hash = request.args.get("commit_hash", 0, type=str)
    item_hash = request.args.get("item_hash", 0, type=str)
    item_path = request.args.get("item_path", None, type=str)

    commit_link = request.args.get("commit_link", "", type=str)
    repo_url = request.args.get("repo_url", "", type=str)

    if "github.com" in commit_link:
        resource_url = commit_link
    else:
        resource_url = repo_url or commit_link

    vcs_handler = get_vcs_handler(app, resource_url)
    if not vcs_handler:
        return create_json_response("Please provide a valid resource URL.", 400)

    # try:
    # Return a specific file's content if requested instead.
    if item_hash:
        content = vcs_handler.get_file_content(item_hash, item_path)
        if not content:
            err = f"Could not retrieve object with hash {item_hash}."
            logging.error(err)
            return create_json_response(str(err), 400)
        logging.info("Retrieved %s: %d  bytes", item_hash, len(content))
        return content
    return vcs_handler.fetch_commit_data(commit_hash)
    # except Exception as err:
    #  if DEBUG:
    #    return create_json_response(str(err), 400, tb=traceback.format_exc())
    #  else:
    #    return create_json_response(str(err), 400)


app.register_blueprint(bp)


def enable_cloud_logging():
    import google.cloud.logging  # pylint: disable=import-outside-toplevel
    import google.auth.exceptions  # pylint: disable=import-outside-toplevel

    print("[*] Enabling cloud logging")
    # Instantiates a client
    try:
        client = google.cloud.logging.Client()

        # Retrieves a Cloud Logging handler based on the environment
        # you're running in and integrates the handler with the
        # Python logging module. By default this captures all logs
        # at INFO level and higher
        print("Default handler:", client.get_default_handler())
        client.setup_logging(log_level="WARNING")
        print("[+] Cloud logging enabled:", logging.getLogger().handlers)
    except google.auth.exceptions.DefaultCredentialsError:
        print("[!] Cloud logging not enabled due to missing credentials")


if IS_PROD:
    enable_cloud_logging()


def start():
    root_dir = os.path.dirname(os.path.realpath(__file__))
    error_file = os.path.join(root_dir, "vcs_error.log")

    handler = RotatingFileHandler(error_file, maxBytes=100000, backupCount=1)
    handler.setLevel(logging.WARNING)
    app.logger.addHandler(handler)
    app.logger.addHandler(logging.StreamHandler(stream=sys.stdout))
    if DEBUG:
        app.logger.setLevel(logging.DEBUG)
    else:
        app.logger.setLevel(logging.INFO)

    if "GITHUB_ACCESS_TOKEN" in vcs_config:
        app.config["GITHUB_API_ACCESS_TOKEN"] = vcs_config["GITHUB_ACCESS_TOKEN"]

    cert_dir = os.path.join(root_dir, "cert")
    cert_file = os.path.join(cert_dir, "cert.pem")
    key_file = os.path.join(cert_dir, "key.pem")

    ssl_context = (cert_file, key_file)
    use_host = "0.0.0.0"
    use_port = 8088
    use_protocol = "https" if ssl_context else "http"
    print(f"[+] Listening on: {use_protocol}://{use_host}:{use_port}")
    app.run(host=use_host, port=use_port, ssl_context=ssl_context, debug=DEBUG)


if __name__ == "__main__":
    start()
