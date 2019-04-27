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

function setup_certs() {
  if [[ -d "cert" && -f "cert/key.pem" && -f "cert/cert.pem" ]]; then
      success "Available."
      return
  fi
  mkdir cert &>/dev/null
  cd cert
  openssl req -nodes -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 9999 -subj "/C=US/ST=California/L=SF/O=FOO/OU=BAR/CN=example.com"
  if [[ ! -f "key.pem" || ! -f "cert.pem" ]]; then
    fatal "Can't create certificates."
  fi
  cd ..
  success "Created."
}

info "Making sure all configuration files are available."
setup_yaml app.yaml
setup_yaml vcs_proxy.yaml

info "Making sure SSL certificates for the VCS proxy exist."
setup_certs

info "Setting up all relevant docker containers."
if which docker-compose &>/dev/null
then
  cd docker
  sudo docker-compose build
else
  fatal 'Please install docker-compose.'
fi

info "You should be able to start everything with: cd docker; sudo docker-compose up"
error "Please also see docker/docker-admin.sh for information on how to fill the database and more."
info "Available resources when deployed:"
success "Main application: http://127.0.0.1:8080"
success "VCS proxy: https://127.0.0.1:8088"
