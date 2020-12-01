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

if [[ ! -d "migrations/versions" || ! $(ls -A migrations/versions) ]]; then
  info "Initializing the database with Alembic. Attention: Alembic will likely not reflect all details of the database."
  info "Please make sure to check the migrations/versions/[revision_hash].py against the model definitions in"
  info "data/models/*.py"
  ./manage.sh db init
  ./manage.sh db migrate
  ./manage.sh db upgrade
fi

if [[ $(./manage.sh db current 2>/dev/null | wc -l) -lt 2 ]]; then
  info "Initializing application database to newest version."
  ./manage.sh db upgrade
fi

python3 -c "import main; main.check_db_state()" || exit 1

if which dev_appserver.py &>/dev/null
then
  # Use Google's cloud SDK to start this with a local AppEngine instance.
  dev_appserver.py "$@" app.yaml
  # Optionally, you can start the server under a different port with:
  # dev_appserver.py --port=8090 --admin_port=8089 app.yaml
else
  # Start without GAE support.
  python3 -m main
fi
