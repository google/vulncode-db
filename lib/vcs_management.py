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

from lib.vcs_handler import *
from lib.vcs_handler.vcs_handler import (
    VcsHandler,
    VULN_ID_PLACEHOLDER,
    HASH_PLACEHOLDER,
    PATH_PLACEHOLDER,
)
from app.exceptions import InvalidIdentifierException


def get_inheritor_clases(klass):
    """
    Returns a list of all defined and valid vcs handlers.

    Args:
    klass: Name of parent class.

    Returns:
    List: Defined vcs handlers.
    """
    subclasses = set()
    work = [klass]
    while work:
        parent = work.pop()
        for child in parent.__subclasses__():
            if child not in subclasses:
                subclasses.add(child)
                work.append(child)
    return subclasses


def get_vcs_handler(app, resource_url):
    """
    Tries to instantiate a vcs handler with teh given resource url.

    Args:
    app:
    resource_url:

    Returns:
    Null|VCS object: A valid vcs handler if available.
    """
    new_handler = None
    vcs_handlers = get_inheritor_clases(VcsHandler)
    for vcs_handler in vcs_handlers:
        try:
            new_handler = vcs_handler(app, resource_url)
            logging.debug(
                f"Parsing {resource_url} with {vcs_handler.__name__} succeeded"
            )
        except InvalidIdentifierException as e:
            logging.debug(
                f"Parsing {resource_url} with {vcs_handler.__name__} failed: {e}"
            )
            pass
    return new_handler
