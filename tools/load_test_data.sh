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
# Load analytics test data (session aggregates)
lunes-cms-cli loaddata "${PACKAGE_DIR}/analytics/fixtures/test_data.json"
# The fixture jobs, units and words have no area, i.e. they belong to the
# main app. Area scoping (#1016) hides them from everybody but an
# administrator of the main app area, so the vocabulary manager fixture user
# is assigned there, the same way a real admin would have to do by hand.
lunes-cms-cli shell -c "
from django.contrib.auth import get_user_model
from lunes_cms.cmsv2.models import Area
Area.objects.get(is_main_app=True).admins.add(
    get_user_model().objects.get(username='vanessa.vokabelverwalterin')
)
"
# Restore test media files
git restore --source origin/assets lunes_cms/media
echo "✔ Imported test data" | print_success
