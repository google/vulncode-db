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

from flask import jsonify
import os


def get_file_contents(path):
  with open(path, 'r') as f:
    output = f.read()
  return output


def write_contents(path, content):
  with open(path, 'w') as f:
    f.write(content)


def createJsonResponse(msg, status_code=200, **kwargs):
  message = {'msg': msg}
  message.update(kwargs)
  resp = jsonify(message)
  resp.status_code = status_code
  return resp

  # Load app.yaml environment variables manually.


def manuallyReadAppConfig():
  try:
    import yaml
  except ImportError:
    return
  with open('app.yaml', 'r') as f:
    try:
      yaml_context = yaml.load(f, Loader=yaml.SafeLoader)
      env_variables = yaml_context['env_variables']
      for key in env_variables:
        os.environ[key] = str(env_variables[key])
    except yaml.YAMLError as e:
      print(e)
