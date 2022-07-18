#!/bin/bash

# This script imports test data into the database.

# Import utility functions
# shellcheck source=./tools/_functions.sh
source "$(dirname "${BASH_SOURCE[0]}")/_functions.sh"

require_installed
migrate_database

echo "Importing test data..." | print_info
# Load database contents
lunes-cms-cli loaddata test_data
# Restore test media files
git restore --source origin/assets lunes_cms/media
echo "✔ Imported test data" | print_success
