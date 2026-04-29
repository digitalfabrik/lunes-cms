#!/bin/bash

# Run a Django management command against the lunes-cms project, e.g.
#   ./tools/manage.sh aggregate_analytics
#   ./tools/manage.sh aggregate_analytics --dry-run
#   ./tools/manage.sh dbshell
#
# Compared to invoking ``lunes-cms-cli`` directly, this wrapper makes sure the
# virtualenv is active and the database is migrated, matching the behaviour of
# the other dev scripts.

# Import utility functions
# shellcheck source=./tools/_functions.sh
source "$(dirname "${BASH_SOURCE[0]}")/_functions.sh"

if [[ $# -eq 0 ]]; then
    echo "Usage: $(basename "$0") <command> [args...]" | print_error
    echo "Example: $(basename "$0") aggregate_analytics --dry-run" | print_info
    exit 1
fi

require_database

lunes-cms-cli "$@"
