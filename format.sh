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

if npx eslint &>/dev/null
then
  info 'Formatting *.js files.'
  npx eslint "**/*.js" --fix --quiet  --ignore-path '.gitignore' --ignore-pattern 'static/monaco/' --ignore-pattern 'static/js/third_party' --debug 2>&1 > /dev/null | grep "Processing" | sed 's/^.*Processing\(.*\)$/Reformatting\1/'
else
  error 'Please install eslint. Install node.js and run: npm install'
fi

if which black &>/dev/null
then
  info 'Formatting python files with black'
  black app lib data tests migrations tools *.py || fatal 'Error during formatting python files'
else
  fatal 'Please install black: pip3 install black'
fi

success "Done. Happy coding :)"
