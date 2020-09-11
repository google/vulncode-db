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
from data.models.user import User
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
