#!/bin/bash

# This script imports test data into the database.

# Import utility functions
# shellcheck source=./tools/_functions.sh
source "$(dirname "${BASH_SOURCE[0]}")/_functions.sh"

require_installed
migrate_database

echo "Importing test data..." | print_info
# Load cms test data first (includes auth.user and auth.group)
lunes-cms-cli loaddata "${PACKAGE_DIR}/cms/fixtures/test_data.json"
# Load cmsv2 test data (jobs, units, words)
lunes-cms-cli loaddata "${PACKAGE_DIR}/cmsv2/fixtures/test_data.json"
# Restore test media files
git restore --source origin/assets lunes_cms/media
echo "✔ Imported test data" | print_success
