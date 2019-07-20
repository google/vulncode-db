#!/usr/bin/env bash
BASEDIR="$( cd "$( dirname "$0" )" && pwd )"

# Make sure we are in the project root directory before executing the test runner.
cd ${BASEDIR}/../

PYTHONPATH="third_party" python3 -m unittest discover -v
# Alternatively, we could also use nose2 as our test runner.
# nose2 -v

# See coverage with:
# coverage run -m tests.lib.test_utils
# Show which lines are not covered.
# coverage report -m lib/*.py
# coverage html lib/*.py