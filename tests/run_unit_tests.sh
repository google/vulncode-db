#!/usr/bin/env bash
BASEDIR="$( cd "$( dirname "$0" )" && pwd )"

# Make sure we are in the project root directory before executing the test runner.
cd ${BASEDIR}/../

pytest \
  --cov-config=.coveragerc \
  --cov-report html \
  --cov=app \
  --cov=lib \
  --cov=data \
  -m 'not integration' \
  tests "$@"
