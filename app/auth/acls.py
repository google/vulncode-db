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

from flask_bouncer import Bouncer, requires, ensure, skip_authorization  # type: ignore
from bouncer.models import RuleList  # type: ignore
from bouncer.constants import ALL, MANAGE, READ  # type: ignore
from werkzeug.exceptions import Forbidden

from data.models.user import User

__all__ = ["skip_authorization", "bouncer", "requires", "ensure"]

bouncer = Bouncer()
log = logging.getLogger(__name__)


@bouncer.authorization_method
def authorize(user: User, they: RuleList):
    def per_role(cls):
        """Reads _permissions from the given class and creates rules from it."""
        perms = getattr(cls, "_permissions")
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
                elif hasattr(check, "__call__"):

                    def gen_wrapper(check):
                        def wrapper(subject):
                            return check(subject, user)

                        return wrapper

                    they.can(action, cls, gen_wrapper(check))
                else:
                    they.can(action, cls, check)

    if user is not None:
        they.can(MANAGE, User, id=user.id)
        they.can(READ, User)
        they.can("READ_OWN", "Proposal")
        if user.is_reviewer():
            # reviewers can see the list of proposals
            they.can(READ, "Proposal")
        if user.is_admin():
            # admins can do everything
            they.can(MANAGE, ALL)

    # pylint: disable=import-outside-toplevel
    # import locally to avoid import cycle
    from data.models.vulnerability import Vulnerability

    # pylint: enable=import-outside-toplevel

    per_role(Vulnerability)

    log.debug("%s can %s", user, they)


def login_required(do_redirect=True):
    def decorator(func):
        return func

    del do_redirect
    return decorator


def admin_required(do_redirect=False):
    del do_redirect
    try:
        return requires(MANAGE, ALL)
    except Forbidden as ex:
        log.warning("Denied admin access: %s", ex.description)
        raise
