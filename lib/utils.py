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

import os
import re
import time
import sys
from functools import wraps

from flask import jsonify, request
from sqlakeyset import unserialize_bookmark  # type: ignore

TRACING_PATH = "traces/"
TRACING_ACTIVE = False
TRACING_LOGGING = False
TRACING_FILE_HANDLE = None


def get_file_contents(path):
    with open(path) as file:
        output = file.read()
    return output


def write_contents(path, content):
    with open(path, "w") as f:
        f.write(content)


def create_json_response(msg, status_code=200, **kwargs):
    message = {"msg": msg}
    message.update(kwargs)
    resp = jsonify(message)
    resp.status_code = status_code
    return resp


def manually_read_app_config():
    """Load app.yaml environment variables manually."""
    try:
        import yaml
    except ImportError:
        return None
    with open("app.yaml") as file:
        try:
            yaml_context = yaml.load(file, Loader=yaml.SafeLoader)
            env_variables = yaml_context["env_variables"]
            for key in env_variables:
                os.environ[key] = str(env_variables[key])
        except yaml.YAMLError as err:
            print(err)


def measure_execution_time(label):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            res = func(*args, **kwargs)
            end = time.time()

            print(f"[{label}] {end - start}s elapsed")
            return res

        return wrapper

    return decorator


def filter_pagination_param(param):
    filtered = re.sub(r'[^a-zA-Z\d\- <>:~]', '', param)
    return filtered


def parse_pagination_param(param_key):
    pagination_param = request.args.get(param_key, None)
    if not pagination_param:
        return False
    sanitized_param = filter_pagination_param(pagination_param)
    unserialized_pagination = unserialize_bookmark(sanitized_param)
    return unserialized_pagination


def function_hooking_wrap(original_function, hooking_function):
    """
    Allows to hook a given function with a provided hooking function.
    :param original_function:
    :param hooking_function:
    :return:
    """
    @wraps(original_function)
    def hook(*args, **kwargs):
        hooking_function(*args, **kwargs)
        return original_function(*args, **kwargs)

    return hook


def log_trace(text):
    global TRACING_ACTIVE, TRACING_FILE_HANDLE
    if not TRACING_ACTIVE or not TRACING_FILE_HANDLE:
        return
    TRACING_FILE_HANDLE.write(text + "\n")


def trace_func(frame, event, arg, stack_level=[0]):
    if event == "call":
        stack_level[0] += 2
        func_name = frame.f_code.co_name
        line_no = frame.f_lineno
        file_name = frame.f_code.co_filename
        trace_info = "-" * stack_level[0] + "> {} - {}:{}".format(
            file_name, func_name, line_no)
        log_trace(trace_info)
        print(trace_info)
    elif event == "return":
        stack_level[0] -= 2
    return trace_func


def enable_tracing(enabled=True):
    """
    Tracing function to monitor application behavior in detail.

    Usage:
    enable_tracing(True)
    CRITICAL_STATEMENT/s
    enable_tracing(False)

    :param enabled: If to enable or disable the tracing.
    :return:
    """
    global TRACING_PATH, TRACING_ACTIVE, TRACING_FILE_HANDLE
    if enabled:
        if TRACING_ACTIVE:
            return
        TRACING_ACTIVE = True
        if not os.path.exists(TRACING_PATH):
            os.makedirs(TRACING_PATH)

        trace_file = time.strftime("trace_%Y%m%d-%H%M%S")
        TRACING_FILE_HANDLE = open(TRACING_PATH + trace_file, "a+")
        log_trace("-- Tracing Start --")
        sys.setprofile(trace_func)
    else:
        sys.setprofile(None)
        log_trace("-- Tracing End --")
        TRACING_FILE_HANDLE.close()
        TRACING_FILE_HANDLE = None
        TRACING_ACTIVE = False
