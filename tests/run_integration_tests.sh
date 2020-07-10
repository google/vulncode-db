#!/usr/bin/env bash
set -e

BASEDIR="$( cd "$( dirname "$0" )" && pwd )"
export COOKIE_SECRET_KEY="${COOKIE_SECRET_KEY:-no so secret}"

if [[ ! "${BASEDIR}" == "/app/tests" && -z "${SQLALCHEMY_DATABASE_URI}" && -z "${MYSQL_HOST}" ]]; then
  echo "[!] The tests currently require a MySQL backend."
  echo "[!] Please execute this instead through Docker with:"
  echo -e "\tdocker/docker-admin.sh test"
  echo "[!] or set SQLALCHEMY_DATABASE_URI or MYSQL_HOST"
  exit
fi

export SQLALCHEMY_DATABASE_URI="${SQLALCHEMY_DATABASE_URI:-mysql+mysqldb://${MYSQL_USER:-root}:${MYSQL_PWD:-test_db_pass}@${MYSQL_HOST}:${MYSQL_PORT:-3306}/main}"

# Make sure we are in the project root directory before executing the test runner.
cd ${BASEDIR}/../

# More pytest options:
# -s:           To disable stdout capturing / to always show stdout.
# -k "keyword": Filter tests for a specific keyword.

if [ "${TEST_FILTER}" != "" ]
then
  TEST_ARGS="${TEST_ARGS} -k ${TEST_FILTER}"
fi
args=( $TEST_ARGS )

pytest -vv \
  --cov-config=.coveragerc \
  --cov-report html \
  --cov=app \
  --cov=lib \
  --cov=data \
  --cov=templates \
  --log-level=DEBUG \
  --color=yes \
  "${args[@]}" \
  tests
