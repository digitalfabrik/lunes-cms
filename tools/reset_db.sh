#!/bin/bash

# This script resets the local development database: it deletes the existing
# SQLite database file, runs migrations from scratch and re-imports the test
# data fixtures (including an admin user and basic vocabulary).

# Import utility functions
# shellcheck source=./tools/_functions.sh
source "$(dirname "${BASH_SOURCE[0]}")/_functions.sh"

require_installed

echo "Removing existing SQLite database..." | print_info
rm -f "${PACKAGE_DIR}/db.sqlite3"
echo "✔ Removed existing SQLite database" | print_success

# Migrate the fresh database and re-import the test data fixtures
bash "${DEV_TOOL_DIR}/load_test_data.sh"

echo -e "\n✔ Database was successfully reset 😻" | print_success
