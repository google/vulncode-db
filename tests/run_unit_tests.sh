#!/usr/bin/env bash
set -e

BASEDIR="$( cd "$( dirname "$0" )" && pwd )"

# Make sure we are in the project root directory before executing the test runner.
cd ${BASEDIR}/../

export COOKIE_SECRET_KEY=not-so-secret

pytest \
  --cov-config=.coveragerc \
  --cov-report html \
  --cov=app \
  --cov=lib \
  --cov=data \
  --color=yes \
  -m 'not integration' \
  tests "$@"
