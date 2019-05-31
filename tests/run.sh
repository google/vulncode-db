#!/usr/bin/env bash
BASEDIR="$( cd "$( dirname "$0" )" && pwd )"

if [[ ! "${BASEDIR}" == "/app/tests" ]]; then
  echo "[!] The tests currently require a MySQL backend."
  echo "[!] Please execute this instead through Docker with:"
  echo -e "\tdocker/docker-admin.sh test"
  exit
fi

# Make sure we are in the project root directory before executing the test runner.
cd ${BASEDIR}/../

python -m unittest discover -v
# Alternatively, we could also use nose2 as our test runner.
# nose2 -v

# See coverage with:
# coverage run -m tests.lib.test_utils
# Show which lines are not covered.
# coverage report -m lib/*.py
# coverage html lib/*.py