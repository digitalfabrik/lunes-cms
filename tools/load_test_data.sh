#!/bin/bash

# This script imports test data into the database.

# Import utility functions
source "$(dirname "${BASH_SOURCE[0]}")/_functions.sh"

require_installed
migrate_database

echo "Importing test data..." | print_info
lunes-cms-cli loaddata test_data
echo "✔ Imported test data" | print_success
