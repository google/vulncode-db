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
from typing import Iterable, Optional, TypeVar, Type, overload

# import all implementations
from lib.vcs_handler import *  # pylint: disable=wildcard-import
from lib.vcs_handler.vcs_handler import (
    VcsHandler,
    VCDB_ID_PLACEHOLDER,
    HASH_PLACEHOLDER,
    PATH_PLACEHOLDER,
)
from app.exceptions import InvalidIdentifierException

__all__ = [
    "VCDB_ID_PLACEHOLDER",
    "HASH_PLACEHOLDER",
    "PATH_PLACEHOLDER",
]

T = TypeVar("T")  # pylint: disable=invalid-name


# https://github.com/python/mypy/issues/4717#issuecomment-582273171
@overload
def get_inheritor_clases(klass: Type[T]) -> Iterable[Type[T]]:
    pass


@overload
def get_inheritor_clases(klass: type) -> Iterable[Type[T]]:
    pass


def get_inheritor_clases(klass: Type[T]) -> Iterable[Type[T]]:
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


def get_vcs_handler(app, resource_url: str) -> Optional[VcsHandler]:
    """
    Tries to instantiate a vcs handler with the given resource url.

    Args:
        app:
        resource_url:

    Returns:
        None|VCS object: A valid vcs handler if available.
    """
    new_handler = None
    vcs_handlers: Iterable[Type[VcsHandler]] = get_inheritor_clases(VcsHandler)
    for vcs_handler in vcs_handlers:
        try:
            new_handler = vcs_handler(app, resource_url)
            logging.debug(
                "Parsing %s with %s succeeded",
                resource_url,
                vcs_handler.__name__,
            )
            break
        except InvalidIdentifierException as ex:
            logging.debug(
                "Parsing %s with %s failed: %s", resource_url, vcs_handler.__name__, ex
            )
    return new_handler


def get_vcs_handler_by_repo_hash(
    app, repo_url: str, commit_hash: str
) -> Optional[VcsHandler]:
    """
    Tries to instantiate a vcs handler with the given repo url and hash.

    Args:
        app:
        repo_url:
        commit_hash:

    Returns:
        None|VCS object: A valid vcs handler if available.
    """
    new_handler = None
    vcs_handlers: Iterable[Type[VcsHandler]] = get_inheritor_clases(VcsHandler)
    for vcs_handler in vcs_handlers:
        try:
            new_handler = vcs_handler(app)
            new_handler.parse_url_and_hash(repo_url, commit_hash)
            logging.debug(
                "Parsing %s+%s with %s succeeded",
                repo_url,
                commit_hash,
                vcs_handler.__name__,
            )
            break
        except InvalidIdentifierException as ex:
            logging.debug(
                "Parsing %s+%s with %s failed: %s",
                repo_url,
                commit_hash,
                vcs_handler.__name__,
                ex,
            )
    return new_handler
