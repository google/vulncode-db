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

function setup_yaml() {
  example_file="example_${1}"
  target_file=$1
  info "Checking for ${target_file} existence."
  if [[ -f $target_file ]]; then
    success "Available."
    return
  fi
  cp $example_file $target_file
  if [[ ! -f $target_file ]]; then
    fatal "Can't create ${target_file}. Is ${example_file} still present?"
  fi
  success "Created."
}

info "Making sure all configuration files are available."
setup_yaml app.yaml
setup_yaml vcs_proxy.yaml

info "Setting up all relevant docker containers."

if which docker-compose &>/dev/null
then
  cd docker
  sudo docker-compose build
else
  fatal 'Please install docker-compose.'
fi

info "You should be able to start everything with: cd docker; sudo docker-compose up"

