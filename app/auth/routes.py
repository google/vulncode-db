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
from typing import Optional, Tuple

import jinja2

from flask import (
    session,
    request,
    url_for,
    redirect,
    Blueprint,
    g,
    current_app,
    flash,
    render_template,
    Response,
)
from authlib.integrations.flask_client import OAuth  # type: ignore
from flask_wtf import FlaskForm  # type: ignore
from wtforms import BooleanField  # type: ignore
from wtforms.validators import DataRequired  # type: ignore
import werkzeug

from app.auth.acls import skip_authorization
from data.database import DEFAULT_DATABASE
from data.models.user import (
    InviteCode,
    User,
    Role,
    PredefinedRoles,
    UserState,
    LoginType,
)

bp = Blueprint("auth", __name__, url_prefix="/auth")
db = DEFAULT_DATABASE.db
log = logging.getLogger(__name__)

GGOGLE_MINIMAL_SCOPES = "openid email"
GOOGLE_FULL_SCOPES = GGOGLE_MINIMAL_SCOPES + " profile"
GITHUB_SCOPES = "read:user"

oauth = OAuth()  # pylint: disable=invalid-name
oauth.register(
    name="google",
    api_base_url="https://www.googleapis.com/",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": GGOGLE_MINIMAL_SCOPES},
)
oauth.register(  # nosec
    name="github",
    api_base_url="https://api.github.com/",
    authorize_url="https://github.com/login/oauth/authorize",
    access_token_url="https://github.com/login/oauth/access_token",
    client_kwargs={"scope": "read:user"},
)


def _login_local(as_user: str):
    if as_user in current_app.config["APPLICATION_ADMINS"]:
        session["user_info"] = {
            "email": as_user,
            "name": "Admin " + as_user.split("@", 1)[0],
            # https://de.wikipedia.org/wiki/Datei:User-admin.svg
            "picture": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a6/User-admin.svg/170px-User-admin.svg.png",  # pylint: disable=line-too-long
            "type": LoginType.LOCAL,
        }
    elif as_user == "reviewer@vulncode-db.com":
        session["user_info"] = {
            "email": as_user,
            "name": "Reviewer",
            # https://de.wikipedia.org/wiki/Datei:Magnifying_glass_icon.svg
            "picture": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Magnifying_glass_icon.svg/240px-Magnifying_glass_icon.svg.png",  # pylint: disable=line-too-long
            "type": LoginType.LOCAL,
        }
    elif as_user == "user@vulncode-db.com":
        session["user_info"] = {
            "email": as_user,
            "name": "User 1",
            # https://de.wikipedia.org/wiki/Datei:User_font_awesome.svg
            "picture": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7c/User_font_awesome.svg/240px-User_font_awesome.svg.png",  # pylint: disable=line-too-long
            "type": LoginType.LOCAL,
        }
    else:
        return render_template(
            "local_login.html", users=current_app.config["APPLICATION_ADMINS"]
        )

    flash("Bypassed OAuth on local dev environment.", "info")
    return redirect(session.pop("redirect_path", "/"))


def _login_google():
    if request.form.get("fetch_profile") != "true":
        return oauth.google.authorize_redirect(
            redirect_uri=url_for("auth.authorized_google", _external=True)
        )

    return oauth.google.authorize_redirect(
        redirect_uri=url_for("auth.authorized_google", _external=True),
        scope=GOOGLE_FULL_SCOPES,
    )


def _login_github():
    if request.form.get("fetch_profile") != "true":
        return oauth.github.authorize_redirect(
            redirect_uri=url_for("auth.authorized_github", _external=True),
        )
    return oauth.github.authorize_redirect(
        redirect_uri=url_for(
            "auth.authorized_github", _external=True, fetch_profile="true"
        ),
    )


@bp.route("/login", methods=["GET", "POST"])
@skip_authorization
def login():
    if is_authenticated():
        return redirect("/")

    # Allow OAuth bypass on local dev environment.
    as_user = request.args.get("as_user", None, type=str)
    if as_user == "Google":
        return _login_google()
    if as_user == "Github":
        return _login_github()
    if current_app.config["IS_LOCAL"]:
        return _login_local(as_user)
    return render_template("login.html")


@bp.route("/invite/<invite_code>", methods=["GET"])
@skip_authorization
def invite(invite_code: str):
    session["invite_code"] = invite_code
    return redirect(url_for("auth.login"))


@bp.route("/logout", methods=["GET"])
@skip_authorization
def logout():
    session.clear()
    g.user = None
    return redirect("/")


@bp.route("/authorized/google")
@bp.route("/authorized")
@skip_authorization
def authorized_google():
    if "error_reason" in request.args:
        error_message = "Access denied"
        error_message += f": reason={request.args['error_reason']}"
        error_message += f" error={request.args['error_description']}"
        return Response(error_message, mimetype="text/plain")

    token = oauth.google.authorize_access_token()
    user = oauth.google.parse_id_token(token)
    session["user_info"] = user
    session["user_info"]["type"] = LoginType.GOOGLE

    if User.query.filter_by(login=user["email"]).one_or_none() is None:
        resp, _ = registration_required(user["email"])
        if resp is not None:
            return resp

    do_redirect = session.pop("redirect_path", "/")
    return redirect(do_redirect)


@bp.route("/authorized/github")
@skip_authorization
def authorized_github():
    if "error" in request.args:
        error_message = "Access denied"
        error_message += f": reason={request.args['error']}"
        error_message += f" error={request.args['error_description']}"
        return Response(error_message, mimetype="text/plain")

    oauth.github.authorize_access_token()
    user = oauth.github.get("/user").json()
    session["user_info"] = user
    session["user_info"]["type"] = LoginType.GITHUB

    if request.args.get("fetch_profile") != "true":
        del session["user_info"]["avatar_url"]
        del session["user_info"]["name"]

    if User.query.filter_by(login=user["login"]).one_or_none() is None:
        resp, _ = registration_required(user["login"])
        if resp is not None:
            return resp

    do_redirect = session.pop("redirect_path", "/")
    return redirect(do_redirect)


class TermsAndConditionsForm(FlaskForm):
    terms = BooleanField(
        "I have read and accept the terms and conditions", validators=[DataRequired()]
    )
    # conditions = BooleanField('', validators=[DataRequired()])


@bp.route("/terms", methods=["GET", "POST"])
@skip_authorization
def terms():
    if (
        request.args.get("text", "false").lower() == "true"
        or "user_info" not in session
    ):
        return render_template("terms_text.html")

    form = TermsAndConditionsForm()
    if form.validate_on_submit():
        session["terms_accepted"] = True

        do_redirect = session.pop("redirect_path", "/")
        return redirect(do_redirect)
    return render_template("terms.html", form=form)


def is_admin():
    if is_authenticated():
        login_id = session["user_info"].get("email")
        # TODO: use DB roles?
        if login_id in current_app.config["APPLICATION_ADMINS"]:
            return True
    return False


def get_or_create_role(name) -> Role:
    role = Role.query.filter_by(name=name).first()
    if not role:
        role = Role(name=name)
        db.session.add(role)
    return role


def registration_required(
    login_id=None,
) -> Tuple[Optional[werkzeug.Response], Optional[InviteCode]]:
    # pylint: disable=too-many-return-statements
    if current_app.config["REGISTRATION_MODE"] == "CLOSED":
        if login_id and login_id in current_app.config["APPLICATION_ADMINS"]:
            return None, None
        logout()
        flash("Registration is closed", "danger")
        return redirect("/"), None

    invite_code = None
    if current_app.config["REGISTRATION_MODE"] == "INVITE_ONLY":
        invite_code = InviteCode.query.filter_by(
            code=session.get("invite_code")
        ).one_or_none()
        if not invite_code:
            if login_id and login_id in current_app.config["APPLICATION_ADMINS"]:
                return None, None
            logout()
            flash("Registration is invite only", "danger")
            return redirect("/"), None
        if invite_code.remaining_uses < 1:
            logout()
            flash("Invitation code has expired", "danger")
            return redirect("/"), None

    if not session.get("terms_accepted"):
        log.warning("Terms not accepted yet")
        return redirect(url_for("auth.terms")), None
    return None, invite_code


@bp.before_app_request
def load_user():
    # pylint: disable=too-many-return-statements,too-many-branches
    # TODO: split into smaller functions

    # continue for assets
    if request.path.startswith("/static"):
        return

    # continue for logout page
    if request.path == url_for("auth.logout"):
        return

    # continue for terms page
    if request.path == url_for("auth.terms"):
        return

    if not is_authenticated():
        g.user = None
        return

    log.debug("Loading user")

    # Ignore all non-admin users during maintenance or restricted mode.
    if (
        current_app.config["MAINTENANCE_MODE"]
        or current_app.config["RESTRICT_LOGIN"]
        and not current_app.config["IS_LOCAL"]
    ) and not is_admin():
        logout()
        flash("Login restricted.", "danger")
        return

    # don't override existing user
    if getattr(g, "user", None) is not None:
        log.debug("Reusing existing user %s", g.user)
        return

    data = session["user_info"]

    # Make sure old and incompatible sessions get dropped.
    if "type" not in data.keys():
        logout()
        return

    login_type = LoginType(data["type"])

    if login_type in (LoginType.GOOGLE, LoginType.LOCAL):
        login_id = data["email"]
        picture = data.get("picture")
    elif login_type == LoginType.GITHUB:
        login_id = data["login"]
        picture = data.get("avatar_url")
    else:
        log.error("Unsupported login type %r", login_type)
        flash("Login unsupported.", "danger")
        logout()
        return
    user = User.query.filter_by(login=login_id).one_or_none()
    is_new = False
    is_changed = False
    if not user:
        resp, invite_code = registration_required(login_id=login_id)
        if resp is not None:
            return resp

        if "@" in login_id:
            name, host = login_id.rsplit("@", 1)
            log.info(
                "Creating new user %s...%s@%s (%s)", name[0], name[-1], host, login_type
            )
        else:
            name = login_id
            log.info(
                "Creating new user %s...%s (%s)",
                login_id[:2],
                login_id[-2:],
                login_type,
            )
        user = User(
            login=login_id,
            full_name=data.get("name", name),
            profile_picture=picture,
            login_type=login_type,
        )
        is_new = True
        if invite_code is not None:
            session.pop("invite_code")
            user.roles = invite_code.roles
            user.invite_code = invite_code
            invite_code.remaining_uses -= 1
            if current_app.config["AUTO_ENABLE_INVITED_USERS"]:
                user.enable()
            db.session.add(invite_code)
        elif current_app.config["REGISTRATION_MODE"] == "OPEN":
            user.enable()
    else:
        log.info("Updating user %s", user)
        if "name" in data and not user.full_name:
            user.full_name = data["name"]
            is_changed = True
        if picture and not user.profile_picture:
            user.profile_picture = picture
            is_changed = True
        if user.login_type is None:
            user.login_type = login_type

    # update automatic roles
    if is_new:
        user.roles.append(get_or_create_role(PredefinedRoles.USER))

    email = data.get("email")
    if email in current_app.config["APPLICATION_ADMINS"]:
        user.roles.append(get_or_create_role(PredefinedRoles.ADMIN))
        user.roles.append(get_or_create_role(PredefinedRoles.REVIEWER))
        if is_new:
            user.state = UserState.ACTIVE
        is_changed = True
    elif email == "reviewer@vulncode-db.com":
        user.roles.append(get_or_create_role(PredefinedRoles.REVIEWER))
        is_changed = True

    if is_changed or is_new:
        log.info("Saving user %s", user)
        db.session.add(user)
        db.session.commit()

    if user.is_blocked():
        logout()
        flash("Account blocked", "danger")
    elif user.is_enabled():
        g.user = user
        log.debug("Loaded user %s", g.user)
        if user.is_first_login():
            user.enable()
            db.session.add(user)
            db.session.commit()
            flash(
                jinja2.Markup(
                    "Welcome to Vulncode-DB!<br>"
                    "Please take a look at your "
                    f'<a href="{url_for("profile.index")}">profile page</a> '
                    "to review your settings."
                ),
                "info",
            )
    else:
        logout()
        flash("Account not yet activated", "danger")


def is_authenticated():
    return "user_info" in session
