#!/usr/bin/env bash
set -e

BASEDIR="$( cd "$( dirname "$0" )" && pwd )"

# Make sure we are in the project root directory before executing the test runner.
cd ${BASEDIR}/../

pytest -vv \
  --cov-config=.coveragerc \
  --cov-report html \
  --cov=app \
  --cov=lib \
  --cov=data \
  --cov=templates \
  --log-level=DEBUG \
  --color=yes \
  -m 'production' \
  tests
