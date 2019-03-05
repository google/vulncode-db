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

# Not necessary as third_party is by default considered through the app.yaml config.
#source env/bin/activate

PYTHONPATH="third_party" python -c "import main; main.check_db_state()" || exit 1

# Start a local instance running on :8080 by default.
dev_appserver.py "$@" app.yaml
# Optionall you can start the server under a different port with:
# dev_appserver.py --port=8090 --admin_port=8089 app.yaml