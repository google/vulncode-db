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
  echo -e "[\e[94m*\e[0m]" "$@"
}

function error() {
  echo -e "[\e[91m!\e[0m]" "$@"
}

function success() {
  echo -e "[\e[92m+\e[0m]" "$@"
}

function fatal() {
  error "$@"
  exit 1
}

if npx eslint &>/dev/null
then
  info 'Formatting *.js files.'
  npx eslint "**/*.js" --fix --quiet --ignore-path .gitignore --debug 2>&1 > /dev/null | grep "Processing" | sed 's/^.*Processing\(.*\)$/Reformatting\1/'
else
  fatal 'Please install eslint. Install node.js and run: npm install'
fi

if which yapf &>/dev/null
then
  info 'Formatting python files with yapf'
  YAPF_STYLE='{based_on_style: pep8, indent_width: 4}'
  find . -maxdepth 1 -name "*.py" -print -exec yapf -i --style="${YAPF_STYLE}" {} \; | awk '{print "Reformatting "$1}'
  yapf -p -vv -i --recursive app lib data tests --style="${YAPF_STYLE}" || fatal 'Error during formatting python files'
else
  fatal 'Please install yapf: pip3 install yapf'
fi

#if which black &>/dev/null
#then
#  info 'Formatting python files with black'
#  find . -maxdepth 1 -name "*.py" -exec black {} \;
#  black app lib data || fatal 'Error during formatting python files'
#else
#  fatal 'Please install black: pip3 install black'
#fi

success "Done. Happy coding :)"
