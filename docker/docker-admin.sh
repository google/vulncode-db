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

# Make sure we're in ./docker/
cd "$(dirname "$0")"

DB_PATH="root:pass@tcp(database:3306)/cve?parseTime=true"

function die () {
  echo >&2 "$@"
  exit 1
}

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

function load_cwe_data() {
  info "Loading and importing CWE data."
  sudo docker-compose -f docker-compose.yml -f docker-compose.admin.yml run go-cve-dictionary \
  /vuls/fetch_cwe.sh
}

function load_current_year_cve_data() {
  info "Loading and importing CVE entries of this year."
  CURRENT_YEAR=$(date +"%Y")
  sudo docker-compose -f docker-compose.yml -f docker-compose.admin.yml run go-cve-dictionary \
  go-cve-dictionary fetchnvd -dbtype mysql -dbpath $DB_PATH -years $CURRENT_YEAR
}

function load_latest() {
  info "Loading and importing latest CVE entries."
  sudo docker-compose -f docker-compose.yml -f docker-compose.admin.yml run go-cve-dictionary \
  go-cve-dictionary fetchnvd -dbtype mysql -dbpath $DB_PATH -latest
}

function load_full_cve() {
  info "Loading and importing all CVE entries."
  sudo docker-compose -f docker-compose.yml -f docker-compose.admin.yml run go-cve-dictionary \
  bash -c 'for i in `seq 2002 $(date +"%Y")`; do go-cve-dictionary fetchnvd -years $i; done'
}

function init_data() {
  info "Loading and importing initial data."
  load_cwe_data
  load_current_year_cve_data
}

case "$1" in
  init)
    init_data
    ;;
  cwe_data)
    load_cwe_data
    ;;
  current_year_cve_data)
    load_current_year_cve_data
    ;;
  full_cve)
    load_full_cve
    ;;
  latest)
    load_latest
    ;;
  crawl_patches)
    sudo docker-compose -f docker-compose.yml -f docker-compose.admin.yml run frontend \
    python crawl_patches.py
    ;;
  shell)
    [ "$#" -eq 2 ] || die "Please specify a service."
    USE_SERVICE=$2
    sudo docker-compose -f docker-compose.yml -f docker-compose.admin.yml run $USE_SERVICE \
    sh -c '[ -f /bin/bash ] && (bash || true) || sh'
    ;;
  *)
  echo "Usage: $0 [COMMAND]"
  echo "Commands:"
  echo -e "\t init: Loads some initial data (cwe and current year CVE data)"
  echo -e "\t cwe_data: Load CWE data"
  echo -e "\t current_year_cve_data: Load CVE data for the current year only"
  echo -e "\t full_cve: Load all available CVE entries"
  echo -e "\t latest: Load latest CVE entries (useful for automation)"
  echo -e "\t crawl_patches: Run crawl_patches.py inside the frontend container"
  echo -e "\t shell [service]: Launch a shell inside one of the following services:"
  echo -e "\t\t vcs-proxy"
  echo -e "\t\t database"
  echo -e "\t\t go-cve-dictionary"
  echo -e "\t\t frontend"
  exit 1
esac
success "Done"
