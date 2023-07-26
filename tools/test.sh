#!/bin/bash

# This script executes the tests

# Import utility functions
# shellcheck source=./tools/_functions.sh
source "$(dirname "${BASH_SOURCE[0]}")/_functions.sh"

# Delete outdated code coverage
rm -rf "${BASE_DIR:?}/htmlcov/"

# Require that the database exists and is in the correct state
require_database

# Parse given command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        # Verbosity for pytest
        -v|-vv|-vvv|-vvvv) VERBOSITY="$1";shift;;
    esac
done

# The default pytests args we use
PYTEST_ARGS=("--disable-warnings" "--color=yes" "--cov=lunes_cms" "--cov-report=html" "--ds=lunes_cms.core.settings")

if [[ -n "${VERBOSITY}" ]]; then
    PYTEST_ARGS+=("$VERBOSITY")
else
    PYTEST_ARGS+=("--quiet" "--numprocesses=auto")
fi

pytest "${PYTEST_ARGS[@]}"
echo "✔ Tests successfully completed " | print_success

echo -e "Open the following file in your browser to view the test coverage:\n" | print_info
echo -e "\tfile://${BASE_DIR}/htmlcov/index.html\n" | print_bold
