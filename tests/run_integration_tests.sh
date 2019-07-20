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

PYTHONPATH="third_party" python3 -m unittest discover -v
