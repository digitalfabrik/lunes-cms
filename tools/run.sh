#!/bin/bash

# This script can be used to start the cms together with a postgres database docker container.
# It also includes generating translation files and applying migrations after the docker container is started for the first time.


# Import utility functions
# shellcheck source=./tools/_functions.sh
source "$(dirname "${BASH_SOURCE[0]}")/_functions.sh"

# Skip installation check, migrations and translations if --fast option is given
if [[ "$*" != *"--fast"* ]]; then
    # Require that the database exists and is in the correct state
    require_database
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
