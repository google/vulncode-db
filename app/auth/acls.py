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
import logging

from functools import wraps

from flask_bouncer import Bouncer, requires, skip_authorization, ensure
from bouncer import Rule
from bouncer.constants import ALL, MANAGE, READ
from werkzeug.exceptions import Forbidden

from data.models.user import User

bouncer = Bouncer()
log = logging.getLogger(__name__)


@bouncer.authorization_method
def authorize(user: User, they: Rule):
    def per_role(cls):
        """Reads _permissions from the given class and creates rules from it."""
        perms = getattr(cls, '_permissions')
        if perms is None or user is None:
            return

        # normalize role data type
        perms = {str(role): p for role, p in perms.items()}
        for role in user.roles:
            role_perms = perms.get(role.name)
            if role_perms is None:
                continue

            for action, check in role_perms.items():
                # accept all
                if check == ALL or check is True:
                    they.can(action, cls)
                # based on attribute values
                elif isinstance(check, dict):
                    they.can(action, cls, **check)
                # based on check function
                else:
                    they.can(action, cls, check)

    if user is not None:
        if user.is_reviewer():
            # reviewers can see the list of proposals
            they.can(READ, 'Proposal')
        if user.is_admin():
            # admins can do everything
            they.can(MANAGE, ALL)

    # import locally to avoid import
    from data.models.vulnerability import Vulnerability
    per_role(Vulnerability)

    log.debug('%s can %s', user, they)


def login_required(do_redirect=True):
    def decorator(func):
        return func

    return decorator


def admin_required(do_redirect=False):
    try:
        return requires(MANAGE, ALL)
    except Forbidden as ex:
        log.warning('Denied admin access: %s', ex.description)
        raise
