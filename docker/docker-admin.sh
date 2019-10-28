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

function has-docker-access() {
  if [ -n "$DOCKER_ACCESS" ]
  then
    return $DOCKER_ACCESS
  elif docker info &> /dev/null
  then
    DOCKER_ACCESS=0
    return 0
  else
    DOCKER_ACCESS=1
    return 1
  fi
}

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

function dock-comp() {
  if has-docker-access
  then
    docker-compose -f docker-compose.yml -f docker-compose.admin.yml "$@"
  else
    sudo docker-compose -f docker-compose.yml -f docker-compose.admin.yml "$@"
  fi
}

function dock-comp-non-admin() {
  if has-docker-access
  then
    docker-compose -f docker-compose.yml "$@"
  else
    sudo docker-compose -f docker-compose.yml "$@"
  fi
}

function load_cwe_data() {
  info "Loading and importing CWE data."
  dock-comp run --rm go-cve-dictionary \
    /vuls/fetch_cwe.sh
}

function load_current_year_cve_data() {
  info "Loading and importing CVE entries of this year."
  CURRENT_YEAR=$(date +"%Y")
  dock-comp run --rm go-cve-dictionary \
    go-cve-dictionary fetchnvd -dbtype mysql -dbpath $DB_PATH -years $CURRENT_YEAR
}

function load_latest() {
  info "Loading and importing latest CVE entries."
  dock-comp run --rm go-cve-dictionary \
    go-cve-dictionary fetchnvd -dbtype mysql -dbpath $DB_PATH -latest
}

function load_full_cve() {
  info "Loading and importing all CVE entries."
  for i in `seq 2002 $(date +"%Y")`
  do
    dock-comp run --rm go-cve-dictionary \
      go-cve-dictionary fetchnvd -dbtype mysql -dbpath $DB_PATH -years $i
  done
}

function init_data() {
  info "Loading and importing initial data."
  load_cwe_data
  load_latest
}

function crawl_patches() {
  dock-comp run --rm frontend \
    python3 crawl_patches.py
}

function build_service() {
  USE_SERVICE=$1
  dock-comp build $USE_SERVICE
}

function format_code() {
  USE_SERVICE=$1
  dock-comp run --rm utils './format.sh'
}

function lint_code() {
  USE_SERVICE=$1
  dock-comp run --rm utils './lint.sh'
}

function run_tests() {
  info "Starting tests."
  dock-comp run --rm tests
}

function stop_test_database() {
  info "Stopping the tests MySQL server and removing remaining test data."
  dock-comp rm --stop tests-db
}

function start_shell() {
  USE_SERVICE=$1
  dock-comp run --rm $USE_SERVICE \
    sh -c '[ -f /bin/bash ] && (bash || true) || sh'
}

function start_application() {
  if [ "$#" -eq 1 ]
  then
    info "Starting individual service."
    USE_SERVICE=$1
    dock-comp start $USE_SERVICE
    return
  fi
  info "Available resources when deployed:"
  success "Main application: http://127.0.0.1:8080"
  success "VCS proxy: https://127.0.0.1:8088"
  dock-comp-non-admin up
}

function stop_application() {
  if [ "$#" -eq 1 ]
  then
    info "Stopping individual service."
    USE_SERVICE=$1
    dock-comp stop $USE_SERVICE
    return
  fi
  info "Stopping all services:"
  dock-comp down
}

function logs() {
  dock-comp logs $1
}

function ps() {
  dock-comp ps "$@"
}

function exec() {
  dock-comp exec "$@"
}

function services() {
  ps --services | sort
}

function show_usage_string() {
  COMMAND=$1
  DESCRIPTION=$2
  printf "\t %-20s \t %-50s\n" "$COMMAND" "$DESCRIPTION"
}

case "$1" in
  start)
    start_application $2
    ;;
  stop)
    stop_application $2
    ;;
  logs)
    logs "$2"
    ;;
  ps)
    ps
    ;;
  exec)
    shift
    exec "$@"
    ;;
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
  show_usage_string "start/stop ([service])" "Start/stop all (or one specific) service/s and its dependencies."
  show_usage_string "init" "Loads some initial data: CWE and CVE data from last 8 days."
  show_usage_string "test" "Execute the application tests."
  show_usage_string "stop_testdb" "Stop the test database and remove any remaining test data."
  show_usage_string "cwe_data" "Load CWE id<->description mapping data."
  show_usage_string "current_year_cve_data" "Load CVE data for the current year only."
  show_usage_string "full_cve" "Load all available CVE entries."
  show_usage_string "latest" "Load latest CVE entries (useful for automation)."
  show_usage_string "crawl_patches" "Run crawl_patches.py inside the frontend container."
  show_usage_string "format/lint" "Format/Lint the Python and JS code."
  show_usage_string "build [service]" "(Re)builds a given service."
  show_usage_string "shell [service]" "Launch a shell inside a given service."
  show_usage_string "ps" "List running services."
  show_usage_string "logs [service]" "Show logs of running service(s)."

  echo -e "\t --- Available services ---"
  for svc in $(services)
  do
    echo -e "\t\t $svc"
  done
  exit 1
esac
success "Done"
