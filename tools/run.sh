#!/bin/bash

# This script can be used to start the cms together with a postgres database docker container.
# It also includes generating translation files and applying migrations after the docker container is started for the first time.


# Import utility functions
source "$(dirname "${BASH_SOURCE[0]}")/_functions.sh"

# Skip installation check, migrations and translations if --fast option is given
if [[ "$*" != *"--fast"* ]]; then
    # Require that lunes-cms is installed
    require_installed
    # Check if database already exists
    if [ -f "${PACKAGE_DIR}/db.sqlite3" ]; then
        # Migrate database
        migrate_database
    else
        # Load test data
        bash "${DEV_TOOL_DIR}/load_test_data.sh"
    fi
    # Update translation file
    bash "${DEV_TOOL_DIR}/translate.sh"
else
    # Activate virtual environment
    activate_venv
fi

# Show success message once dev server is up
listen_for_devserver &

# Start Lunes CMS development webserver
lunes-cms-cli runserver "localhost:${LUNES_CMS_PORT}"
