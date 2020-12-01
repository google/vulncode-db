#!/bin/bash
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


function info() {
  echo -e "[\033[94m*\033[0m]" "$@"
}

function error() {
  echo -e "[\033[91m!\033[0m]" "$@"
}

function success() {
  echo -e "[\033[92m+\033[0m]" "$@"
}

function fatal() {
  error "$@"
  exit 1
}

failures=0

if npx eslint &>/dev/null
then
  info 'Linting *.js files with eslint'
  npx eslint **/*.js --ignore-path .gitignore
else
  fatal 'Please install eslint. Install node.js and run: npm install'
fi

if which pylint &>/dev/null
then
  info 'Linting python files with pylint'
  pylint --rcfile=./pylintrc --reports=no --disable=fixme *.py app data lib || failures=$(($failures+1))
else
  fatal 'Please install pylint'
fi

if which bandit &>/dev/null
then
  info 'Checking python files with bandit'
  bandit -r app data lib || failures=$(($failures+1))
else
  fatal 'Please install bandit'
fi

if which mypy &>/dev/null
then
  info 'Linting python files with mypy'
  mypy --warn-unused-ignores app data lib || failures=$(($failures+1))
else
  fatal 'Please install mypy'
fi

if [ $failures -gt 0 ]
then
  fatal "Lint failed"
fi
success "Done. Happy coding :)"
