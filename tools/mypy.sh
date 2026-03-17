#!/bin/bash
BASE_DIR="${BASE_DIR:-.}"

# This script can be used to check the python type annotations with my[py].

# Import utility functions
# shellcheck source=./tools/_functions.sh
source "$(dirname "${BASH_SOURCE[0]}")/_functions.sh"

require_installed

# Run my[py]
echo "Starting type checking with my[py]..." | print_info
export FORCE_COLOR=1
mypy . --scripts-are-modules | sort

echo "✔ Type checking finished" | print_success