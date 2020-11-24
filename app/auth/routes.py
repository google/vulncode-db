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

from flask import (session, request, url_for, redirect, Blueprint, g,
                   current_app, flash, render_template)
from authlib.integrations.flask_client import OAuth  # type: ignore
from flask_wtf import FlaskForm  # type: ignore
from wtforms import BooleanField  # type: ignore
from wtforms.validators import DataRequired  # type: ignore
from werkzeug import Response

from app.auth.acls import skip_authorization
from data.database import DEFAULT_DATABASE
from data.models.user import InviteCode, User, Role, PredefinedRoles, UserState

bp = Blueprint("auth", __name__, url_prefix="/auth")
db = DEFAULT_DATABASE.db
log = logging.getLogger(__name__)

MINIMAL_SCOPES = 'openid email'
FULL_SCOPES = MINIMAL_SCOPES + ' profile'

oauth = OAuth()  # pylint: disable=invalid-name
oauth.register(
    name='google',  # nosec
    api_base_url='https://www.googleapis.com/',
    server_metadata_url=
    'https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': MINIMAL_SCOPES})


@bp.route("/login", methods=["GET", "POST"])
@skip_authorization
def login():
    if is_authenticated():
        return redirect("/")

    # Allow OAuth bypass on local dev environment.
    as_user = request.args.get("as_user", None, type=str)
    if current_app.config["IS_LOCAL"] and as_user != "OAuth":
        if as_user in current_app.config["APPLICATION_ADMINS"]:
            session["user_info"] = {
                'email':
                as_user,
                'name':
                'Admin ' + as_user.split("@", 1)[0],
                # https://de.wikipedia.org/wiki/Datei:User-admin.svg
                'picture':
                'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a6/User-admin.svg/170px-User-admin.svg.png',  # pylint: disable=line-too-long
            }
        elif as_user == 'reviewer@vulncode-db.com':
            session["user_info"] = {
                'email':
                as_user,
                'name':
                'Reviewer',
                # https://de.wikipedia.org/wiki/Datei:Magnifying_glass_icon.svg
                'picture':
                'https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Magnifying_glass_icon.svg/240px-Magnifying_glass_icon.svg.png',  # pylint: disable=line-too-long
            }
        elif as_user == 'user@vulncode-db.com':
            session["user_info"] = {
                'email':
                as_user,
                'name':
                'User 1',
                # https://de.wikipedia.org/wiki/Datei:User_font_awesome.svg
                'picture':
                'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7c/User_font_awesome.svg/240px-User_font_awesome.svg.png',  # pylint: disable=line-too-long
            }
        else:
            return render_template(
                "local_login.html",
                users=current_app.config["APPLICATION_ADMINS"])

        flash("Bypassed OAuth on local dev environment.", 'info')
        return redirect(session.pop("redirect_path", "/"))
    if as_user == 'OAuth':
        if request.form.get('fetch_profile') != 'true':
            return oauth.google.authorize_redirect(
                redirect_uri=url_for("auth.authorized", _external=True))

        return oauth.google.authorize_redirect(redirect_uri=url_for(
            "auth.authorized", _external=True),
                                               scope=FULL_SCOPES)
    return render_template('login.html')


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


@bp.route("/authorized")
@skip_authorization
def authorized():
    if "error_reason" in request.args:
        error_message = "Access denied"
        error_message += f": reason={request.args['error_reason']}"
        error_message += f" error={request.args['error_description']}"
        return error_message

    token = oauth.google.authorize_access_token()
    user = oauth.google.parse_id_token(token)
    session["user_info"] = user

    if User.query.filter_by(email=user['email']).one_or_none() is None:
        resp, _ = registration_required(user['email'])
        if resp is not None:
            return resp

    do_redirect = session.pop("redirect_path", '/')
    return redirect(do_redirect)


class TermsAndConditionsForm(FlaskForm):
    terms = BooleanField('I have read and accept the terms and conditions',
                         validators=[DataRequired()])
    # conditions = BooleanField('', validators=[DataRequired()])


@bp.route("/terms", methods=['GET', 'POST'])
@skip_authorization
def terms():
    if request.args.get(
            'text', 'false').lower() == 'true' or 'user_info' not in session:
        return render_template('terms_text.html')

    form = TermsAndConditionsForm()
    if form.validate_on_submit():
        session['terms_accepted'] = True

        do_redirect = session.pop("redirect_path", '/')
        return redirect(do_redirect)
    return render_template('terms.html', form=form)


def is_admin():
    if is_authenticated():
        email = session["user_info"]["email"]
        if email in current_app.config["APPLICATION_ADMINS"]:
            return True
    return False


def get_or_create_role(name) -> Role:
    role = Role.query.filter_by(name=name).first()
    if not role:
        role = Role(name=name)
        db.session.add(role)
    return role


def registration_required(
        email=None) -> Tuple[Optional[Response], Optional[InviteCode]]:
    # pylint: disable=too-many-return-statements
    if current_app.config["REGISTRATION_MODE"] == "CLOSED":
        if email and email in current_app.config['APPLICATION_ADMINS']:
            return None, None
        logout()
        flash("Registration is closed", "danger")
        return redirect("/"), None

    invite_code = None
    if current_app.config["REGISTRATION_MODE"] == "INVITE_ONLY":
        invite_code = InviteCode.query.filter_by(
            code=session.get('invite_code')).one_or_none()
        if not invite_code:
            if email and email in current_app.config['APPLICATION_ADMINS']:
                return None, None
            logout()
            flash("Registration is invite only", "danger")
            return redirect("/"), None
        if invite_code.remaining_uses < 1:
            logout()
            flash("Invitation code has expired", "danger")
            return redirect("/"), None

    if not session.get('terms_accepted'):
        log.warning('Terms not accepted yet')
        return redirect(url_for('auth.terms')), None
    return None, invite_code


@bp.before_app_request
def load_user():
    # pylint: disable=too-many-return-statements,too-many-branches
    # TODO: split into smaller functions

    # continue for assets
    if request.path.startswith('/static'):
        return

    # continue for logout page
    if request.path == url_for('auth.logout'):
        return

    # continue for terms page
    if request.path == url_for('auth.terms'):
        return

    if not is_authenticated():
        g.user = None
        return

    log.debug('Loading user')

    # Ignore all non-admin users during maintenance or restricted mode.
    if (current_app.config["MAINTENANCE_MODE"]
            or current_app.config['RESTRICT_LOGIN']
            and not current_app.config['IS_LOCAL']) and not is_admin():
        logout()
        flash('Login restricted.', 'danger')
        return

    # don't override existing user
    if getattr(g, 'user', None) is not None:
        log.debug('Reusing existing user %s', g.user)
        return

    data = session["user_info"]
    email = data["email"]

    user = User.query.filter_by(email=email).one_or_none()
    is_new = False
    is_changed = False
    if not user:
        resp, invite_code = registration_required(email=email)
        if resp is not None:
            return resp

        name, host = email.rsplit('@', 1)
        log.info('Creating new user %s...%s@%s', name[0], name[-1], host)
        user = User(email=email,
                    full_name=data.get("name", name),
                    profile_picture=data.get("picture"))
        is_new = True
        if invite_code is not None:
            session.pop("invite_code")
            user.roles = invite_code.roles
            user.invite_code = invite_code
            invite_code.remaining_uses -= 1
            if current_app.config["AUTO_ENABLE_INVITED_USERS"]:
                user.enable()
            db.session.add(invite_code)
    else:
        log.info('Updating user %s', user)
        if 'name' in data and user.full_name != data['name']:
            user.full_name = data["name"]
            is_changed = True
        if 'picture' in data and user.profile_picture != data['picture']:
            user.profile_picture = data["picture"]
            is_changed = True

    # update automatic roles
    if is_new:
        user.roles.append(get_or_create_role(PredefinedRoles.USER))

    if email in current_app.config["APPLICATION_ADMINS"]:
        user.roles.append(get_or_create_role(PredefinedRoles.ADMIN))
        user.roles.append(get_or_create_role(PredefinedRoles.REVIEWER))
        if is_new:
            user.state = UserState.ACTIVE
        is_changed = True
    elif email == 'reviewer@vulncode-db.com':
        user.roles.append(get_or_create_role(PredefinedRoles.REVIEWER))
        is_changed = True

    if is_changed or is_new:
        log.info('Saving user %s', user)
        db.session.add(user)
        db.session.commit()

    if user.is_blocked():
        logout()
        flash('Account blocked', 'danger')
    elif user.is_enabled():
        g.user = user
        log.debug('Loaded user %s', g.user)
    else:
        logout()
        flash('Account not yet activated', 'danger')


def is_authenticated():
    return 'user_info' in session
