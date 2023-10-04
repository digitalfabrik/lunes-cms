#!/bin/bash

# This script can be used to run pylint

# Import utility functions
# shellcheck source=./tools/_functions.sh
source "$(dirname "${BASH_SOURCE[0]}")/_functions.sh"

require_installed

# Run pylint
echo "Starting code linting with pylint..." | print_info
pylint "lunes_cms/".
echo "✔ Linting finished" | print_success
