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

from flask import (session, request, url_for, abort, redirect, Blueprint, g,
                   current_app, flash, render_template)
from authlib.integrations.flask_client import OAuth, OAuthError  # type: ignore

from data.database import DEFAULT_DATABASE
from data.models import User

bp = Blueprint("auth", __name__, url_prefix="/auth")
db = DEFAULT_DATABASE.db


def fetch_google_token():
    return session.get('google_token')


def update_google_token(token):
    session['google_token'] = token
    return session['google_token']


oauth = OAuth()  # pylint: disable=invalid-name
oauth.register(
    name='google',  # nosec
    api_base_url='https://www.googleapis.com/',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    fetch_token=fetch_google_token,
    update_token=update_google_token,
    client_kwargs={'scope': 'openid email profile'})


@bp.route("/login", methods=["GET"])
def login():
    if is_authenticated():
        return redirect("/")

    # Allow OAuth bypass on local dev environment.
    as_user = request.args.get("as_user", None, type=str)
    if current_app.config["IS_LOCAL"] and as_user != "OAuth":
        if as_user in current_app.config["APPLICATION_ADMINS"]:
            session["user_info"] = {
                'email': as_user,
                'name': 'Admin ' + as_user.split("@", 1)[0],
                'picture': 'https://google.com/',
            }
            session['google_token'] = "1337"
            flash("Bypassed OAuth on local dev environment.")
            return redirect("/")
        return render_template("local_login.html",
                               users=current_app.config["APPLICATION_ADMINS"])

    return oauth.google.authorize_redirect(
        redirect_uri=url_for("auth.authorized", _external=True))


@bp.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect("/")


@bp.route("/authorized")
def authorized():
    if "error_reason" in request.args:
        error_message = "Access denied"
        error_message += f": reason={request.args['error_reason']}"
        error_message += f" error={request.args['error_description']}"
        return error_message

    token = oauth.google.authorize_access_token()
    user = oauth.google.parse_id_token(token)
    session["user_info"] = user

    do_redirect = session.pop("redirect_path", None)
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


def is_authenticated():
    if 'user_info' in session:
        return True

    if 'google_token' not in session:
        return False

    # Allow OAuth bypass on local dev environment.
    if current_app.config["IS_LOCAL"] and session['google_token'] == '1337':
        return True

    try:
        resp = oauth.google.get(
            'https://www.googleapis.com/oauth2/v2/userinfo')
        data = resp.json()
    except OAuthError as ex:
        current_app.logger.exception(
            f"Error during handling the oauth response: {ex.error}")
        del session['google_token']
        return False

    session['user_info'] = data
    return True


def login_required(do_redirect=False):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not is_authenticated():
                if do_redirect:
                    session["redirect_path"] = request.full_path
                    return oauth.google.authorize_redirect(
                        redirect_uri=url_for("auth.authorized",
                                             _external=True))
                return abort(401)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def admin_required(do_redirect=False):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not is_admin():
                if current_app.config["IS_LOCAL"]:
                    flash(
                        "Admin access was granted without login for local dev "
                        "environment.", "success")
                elif do_redirect:
                    session["redirect_path"] = request.full_path
                    return oauth.google.authorize_redirect(
                        redirect_uri=url_for("auth.authorized",
                                             _external=True))
                return abort(401)
            return func(*args, **kwargs)

        return wrapper

    return decorator
