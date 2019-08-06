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

from functools import wraps

from flask import session, request, url_for, abort, redirect, Blueprint, g, current_app, flash
from flask_oauthlib.client import OAuth
from flask_oauthlib.contrib.apps import google

from data.database import DEFAULT_DATABASE
from data.models import User

bp = Blueprint("auth", __name__, url_prefix="/auth")
db = DEFAULT_DATABASE.db

oauth = OAuth()
google = google.register_to(oauth, name="GOOGLE_OAUTH")


@bp.record
def init_auth(state):
    oauth.init_app(state.app)


@bp.route("/login", methods=["GET"])
def login():
    if is_authenticated():
        return redirect("/")
    return google.authorize(
        callback=url_for("auth.authorized", _external=True))


@bp.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect("/")


@bp.route("/authorized")
def authorized():
    try:
        resp = google.authorized_response()
    except Exception:
        current_app.logger.exception(
            "Error during handling the oauth response")
        abort(400)

    if resp is None:
        error_message = "Access denied"
        if "error_reason" in request.args:
            error_message += f": reason={request.args['error_reason']} error={request.args['error_description']}"
        return error_message
    # don't leak access_token into the session cookie
    # session['google_token'] = (resp['access_token'], '')
    do_redirect = session.pop("redirect_path", None)
    me = google.get("userinfo", token=resp["access_token"]).data

    session["user_info"] = me

    if do_redirect:
        return redirect(do_redirect)

    return redirect("/")


def is_admin():
    if is_authenticated():
        email = session["user_info"]["email"]
        if email in current_app.config["APPLICATION_ADMINS"]:
            return True
    return False


@bp.before_app_request
def load_user():
    user = None

    # Ignore all non-admin users for now.
    if not is_admin():
        g.user = None
        return

    # Ignore all non-admin users during maintenance mode.
    if current_app.config["MAINTENANCE_MODE"]:
        return

    if is_authenticated():
        data = session["user_info"]
        email = data["email"]

        user = User.query.filter_by(email=email).one_or_none()
        if not user:
            user = User(email=email,
                        full_name=data["name"],
                        profile_picture=data["picture"])
        else:
            user.full_name = data["name"]
            user.profile_picture = data["picture"]
        db.session.add(user)
        db.session.commit()

    g.user = user


@google.tokengetter
def get_google_oauth_token():
    return session.get("google_token")


def is_authenticated():
    if "user_info" in session:
        return True

    if "google_token" not in session:
        return False

    data = google.get("userinfo").data
    if data.get("error", False):
        del session["google_token"]
        return False

    session["user_info"] = data

    return True


def login_required(redirect=False):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not is_authenticated():
                if redirect:
                    session["redirect_path"] = request.full_path
                    return google.authorize(
                        callback=url_for("auth.authorized", _external=True))
                else:
                    return abort(401)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def admin_required(redirect=False):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not is_admin():
                if current_app.config["IS_LOCAL"]:
                    flash(
                        "Admin access was granted without login for local dev environment.",
                        "success")
                elif redirect:
                    session["redirect_path"] = request.full_path
                    return google.authorize(
                        callback=url_for("auth.authorized", _external=True))
                else:
                    return abort(401)
            return func(*args, **kwargs)

        return wrapper

    return decorator
