#!/bin/bash

# This script executes the tests

# Import utility functions
# shellcheck source=./tools/_functions.sh
source "$(dirname "${BASH_SOURCE[0]}")/_functions.sh"

# Delete outdated code coverage
rm -rf "${BASE_DIR:?}/htmlcov/"

# Require that the database exists and is in the correct state
require_database

pytest --disable-warnings --quiet --numprocesses=auto --cov=lunes_cms --cov-report html --ds=lunes_cms.core.settings
echo "✔ Tests successfully completed " | print_success

echo -e "Open the following file in your browser to view the test coverage:\n" | print_info
echo -e "\tfile://${BASE_DIR}/htmlcov/index.html\n" | print_bold
