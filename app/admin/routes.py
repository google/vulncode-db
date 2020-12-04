# Copyright 2020 Google LLC
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
from flask import Blueprint, render_template, request, flash
from sqlalchemy import or_

from app.auth.acls import admin_required
from data.database import DEFAULT_DATABASE
from data.models.user import InviteCode, User, UserState
from data.models.user import Role

bp = Blueprint("admin", __name__, url_prefix="/admin")
db = DEFAULT_DATABASE


def _assign(role_id, user_ids, new_state):
    del new_state
    role = Role.query.get_or_404(role_id)
    for user_id in user_ids:
        user = User.query.get_or_404(user_id)
        user.roles.append(role)
        yield user


def _unassign(role_id, user_ids, new_state):
    del new_state
    role = Role.query.get_or_404(role_id)
    for user_id in user_ids:
        user = User.query.get_or_404(user_id)
        user.roles.remove(role)
        yield user


def _delete(role_id, user_ids, new_state):
    del role_id, new_state
    for user_id in user_ids:
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
    # don't readd
    db.session.commit()
    return []


def _enable(role_id, user_ids, new_state):
    del role_id, new_state
    for user_id in user_ids:
        user = User.query.get_or_404(user_id)
        user.enable()
        yield user


def _block(role_id, user_ids, new_state):
    del role_id, new_state
    for user_id in user_ids:
        user = User.query.get_or_404(user_id)
        user.block()
        yield user


def _change_state(role_id, user_ids, new_state):
    del role_id
    for user_id in user_ids:
        user = User.query.get_or_404(user_id)
        user.state = UserState[new_state]
        yield user


@bp.route("/users", methods=["GET", "POST"])
@admin_required()
def users():
    if request.method == "POST":
        user_ids = request.form.getlist("user", type=int)
        action = [action for action in request.form.getlist("action") if action][0]
        role_id = request.form.get("role")
        new_state = request.form.get("state")
        changed_users = []
        functions = {
            "assign": _assign,
            "unassign": _unassign,
            "delete": _delete,
            "enable": _enable,
            "block": _block,
            "state": _change_state,
        }
        if action in functions:
            changed_users.extend(
                functions[action](
                    role_id=role_id, user_ids=user_ids, new_state=new_state
                )
            )
        else:
            flash("Invalid action", "danger")

        if changed_users:
            db.session.add_all(changed_users)
            db.session.commit()
            flash(f"Modified {len(changed_users)} user(s)", "success")

    name = request.args.get("name", default="")
    if name:
        query = f"%{name}%"
        user_list = User.query.filter(
            or_(User.login.like(query), User.full_name.like(query))
        ).paginate()
    else:
        user_list = User.query.paginate()
    roles = Role.query.all()

    return render_template(
        "admin/user_list.html",
        users=user_list,
        roles=roles,
        states=list(UserState),
        filter=name,
    )


def _create_invite_token():
    amount = request.form.get("amount", type=int)
    if not amount or amount < 1:
        flash("Invite codes have to be valid for at least one use", "danger")
        return
    roles = request.form.getlist("roles", type=int)
    if not roles or len(roles) == 0:
        flash("At least one role should be selected", "danger")
        return
    desc = request.form.get("desc")
    if not desc:
        flash("Description required", "danger")
        return

    num_roles = len(roles)
    roles = Role.query.filter(Role.id.in_(roles)).all()
    if len(roles) != num_roles:
        flash("Unknown roles provided", "danger")
        return

    db.session.add(InviteCode(roles=roles, remaining_uses=amount, description=desc))
    db.session.commit()


@bp.route("/invite_codes", methods=["GET", "POST"])
@admin_required()
def invite_codes():
    if request.method == "POST":
        if request.form.get("expire_code"):
            icode = InviteCode.query.get_or_404(
                request.form.get("expire_code", type=int)
            )
            icode.remaining_uses = 0
            db.session.add(icode)
            db.session.commit()
        else:
            _create_invite_token()
    invites = InviteCode.query.all()
    roles = Role.query.all()
    return render_template("admin/invite_codes.html", roles=roles, invite_codes=invites)
