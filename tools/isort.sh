#!/bin/bash

# This script can be used to sort the python import statements with isort.

# Import utility functions
# shellcheck source=./tools/_functions.sh
source "$(dirname "${BASH_SOURCE[0]}")/_functions.sh"

require_installed

# Run isort
echo "Sorting import statements with isort..." | print_info
isort . --skip-glob "**/migrations/**"
echo "✔ Sorting finished" | print_success