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
  for i in `seq 2002 $(date +"%Y")`
  do
    sudo docker-compose -f docker-compose.yml -f docker-compose.admin.yml run go-cve-dictionary \
    go-cve-dictionary fetchnvd -dbtype mysql -dbpath $DB_PATH -years $i
  done
}

function init_data() {
  info "Loading and importing initial data."
  load_cwe_data
  load_latest
}

function crawl_patches() {
  sudo docker-compose -f docker-compose.yml -f docker-compose.admin.yml run frontend \
  python crawl_patches.py
}

function build_service() {
  USE_SERVICE=$1
  sudo docker-compose -f docker-compose.yml -f docker-compose.admin.yml build $USE_SERVICE
}

function format_code() {
  USE_SERVICE=$1
  sudo docker-compose -f docker-compose.yml -f docker-compose.admin.yml run utils './format.sh'
}

function lint_code() {
  USE_SERVICE=$1
  sudo docker-compose -f docker-compose.yml -f docker-compose.admin.yml run utils './lint.sh'
}

function run_tests() {
  info "Starting tests."
  sudo docker-compose -f docker-compose.yml -f docker-compose.admin.yml run tests
}

function stop_test_database() {
  info "Stopping the tests MySQL server and removing remaining test data."
  sudo docker-compose -f docker-compose.yml -f docker-compose.admin.yml stop tests-db
}

function start_shell() {
  USE_SERVICE=$1
  sudo docker-compose -f docker-compose.yml -f docker-compose.admin.yml run $USE_SERVICE \
  sh -c '[ -f /bin/bash ] && (bash || true) || sh'
}

case "$1" in
  init)
    init_data
    ;;
  test)
    run_tests
    ;;
  stop_testdb)
    stop_test_database
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
    crawl_patches
    ;;
  format)
    format_code
    ;;
  lint)
    lint_code
    ;;
  build)
    [ "$#" -eq 2 ] || die "Please specify a service."
    build_service $2
    ;;
  shell)
    [ "$#" -eq 2 ] || die "Please specify a service."
    start_shell $2
    ;;
  *)
  echo "Usage: $0 [COMMAND]"
  echo "Commands:"
  echo -e "\t init - Loads some initial data: CWE and CVE data from last 8 days."
  echo -e "\t test - Execute the application tests."
  echo -e "\t stop_testdb - Stop the test database and remove any remaining test data."
  echo -e "\t cwe_data - Load CWE id<->description mapping data."
  echo -e "\t current_year_cve_data - Load CVE data for the current year only."
  echo -e "\t full_cve - Load all available CVE entries."
  echo -e "\t latest - Load latest CVE entries (useful for automation)."
  echo -e "\t crawl_patches - Run crawl_patches.py inside the frontend container."
  echo -e "\t format/lint - Format/Lint the Python and JS code."
  echo -e "\t build [service] - (Re)builds a given service."
  echo -e "\t shell [service] - Launch a shell inside a given service."
  echo -e "\t --- Available services ---"
  echo -e "\t\t vcs-proxy"
  echo -e "\t\t database"
  echo -e "\t\t go-cve-dictionary"
  echo -e "\t\t frontend"
  echo -e "\t\t utils"
  echo -e "\t\t tests"
  exit 1
esac
success "Done"
