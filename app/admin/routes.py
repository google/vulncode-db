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
from data.models.user import InviteCode, User
from data.models.user import Role

bp = Blueprint('admin', __name__, url_prefix='/admin')
db = DEFAULT_DATABASE


@bp.route('/users', methods=['GET', 'POST'])
@admin_required()
def users():
    if request.method == 'POST':
        user_ids = request.form.getlist('user', type=int)
        action = [
            action for action in request.form.getlist('action') if action
        ][0]
        role_id = request.form.get('role')
        changed_users = []
        if action == 'assign':
            role = Role.query.get_or_404(role_id)
            for user_id in user_ids:
                user = User.query.get_or_404(user_id)
                user.roles.append(role)
                changed_users.append(user)
        elif action == 'unassign':
            role = Role.query.get_or_404(role_id)
            for user_id in user_ids:
                user = User.query.get_or_404(user_id)
                user.roles.remove(role)
                changed_users.append(user)
        elif action == 'delete':
            for user_id in user_ids:
                user = User.query.get_or_404(user_id)
                db.session.delete(user)
            db.session.commit()
        elif action == 'enable':
            for user_id in user_ids:
                user = User.query.get_or_404(user_id)
                user.enable()
                changed_users.append(user)
            db.session.commit()
        elif action == 'block':
            for user_id in user_ids:
                user = User.query.get_or_404(user_id)
                user.block()
                changed_users.append(user)
            db.session.commit()
        else:
            flash('Invalid action', 'danger')

        if changed_users:
            db.session.add_all(changed_users)
            db.session.commit()

    name = request.args.get('name', default='')
    if name:
        query = f'%{name}%'
        users = User.query.filter(
            or_(User.email.like(query),
                User.full_name.like(query))).paginate()
    else:
        users = User.query.paginate()
    roles = Role.query.all()

    return render_template('admin/user_list.html',
                           users=users,
                           roles=roles,
                           filter=name)


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

    db.session.add(
        InviteCode(roles=roles, remaining_uses=amount, description=desc))
    db.session.commit()


@bp.route('/invite_codes', methods=['GET', 'POST'])
@admin_required()
def invite_codes():
    if request.method == "POST":
        if request.form.get("expire_code"):
            ic = InviteCode.query.get_or_404(
                request.form.get("expire_code", type=int))
            ic.remaining_uses = 0
            db.session.add(ic)
            db.session.commit()
        else:
            _create_invite_token()
    invites = InviteCode.query.all()
    roles = Role.query.all()
    return render_template('admin/invite_codes.html',
                           roles=roles,
                           invite_codes=invites)
