#!/usr/bin/env bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
flake8 --config="${DIR}/.flake8" "${DIR}/dogkop" "${DIR}/tests"