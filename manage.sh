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


if ! which flask &>/dev/null
then
  echo -e "\e[91mflask not found. Rerun this script within the virtual environment.\e[m"
  exit 1
fi

BASEDIR="$( cd "$( dirname "$0" )" && pwd )"
THIRD_PARTY_DIR="third_party"
# If this is run from Docker all dependencies should be available system wide in the container already.
if [[ "${BASEDIR}" == "/app/" ]]; then
  THIRD_PARTY_DIR=""
fi
PYTHONPATH="${THIRD_PARTY_DIR}" FLASK_APP=main flask "$@"
