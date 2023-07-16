# shellcheck shell=bash

# This file contains utility functions which can be used in the development tools.

# Do not continue execution if one of the commands fail
set -eo pipefail -o functrace

# The Port on which the Lunes CMS development server should be started
LUNES_CMS_PORT=8080
# Change to dev tools directory
cd "$(dirname "${BASH_SOURCE[0]}")"
# The absolute path to the dev tools directory
# shellcheck disable=SC2034
DEV_TOOL_DIR=$(pwd)
# Change to base directory
cd ..
# The absolute path to the base directory of the repository
BASE_DIR=$(pwd)
# The path to the package
PACKAGE_DIR_REL="lunes_cms"
# shellcheck disable=SC2034
PACKAGE_DIR="${BASE_DIR}/${PACKAGE_DIR_REL}"

# This function prints the given input lines in red color
function print_error {
    while IFS= read -r line; do
        echo -e "\x1b[1;31m$line\x1b[0;39m" >&2
    done
}

# This function prints the given input lines in green color
function print_success {
    while IFS= read -r line; do
        echo -e "\x1b[1;32m$line\x1b[0;39m"
    done
}

# This function prints the given input lines in orange color
function print_warning {
    while IFS= read -r line; do
        echo -e "\x1b[1;33m$line\x1b[0;39m"
    done
}

# This function prints the given input lines in blue color
function print_info {
    while IFS= read -r line; do
        echo -e "\x1b[1;34m$line\x1b[0;39m"
    done
}

# This function prints the given input lines in bold white
function print_bold {
    while IFS= read -r line; do
        echo -e "\x1b[1m$line\x1b[0m"
    done
}

# This function prints the given prefix in the given color in front of the stdin lines. If no color is given, white (37) is used.
# This is useful for commands which run in the background to separate its output from other commands.
function print_prefix {
    while IFS= read -r line; do
        echo -e "\x1b[1;${2:-37};40m[$1]\x1b[0m $line"
    done
}

# This function prints the given input lines with a nice little border to separate it from the rest of the content.
# Pipe your content to this function.
function print_with_borders {
    echo "┌──────────────────────────────────────"
    while IFS= read -r line; do
        echo "│ $line"
    done
    echo -e "└──────────────────────────────────────\n"
}

# This function applies different sed replacements to make sure the matched lines from grep are aligned and colored
function format_grep_output {
    while read -r line; do
        echo "$line" | sed --regexp-extended \
            -e "s/^([0-9])([:-])(.*)/\1\2      \3/"         `# Pad line numbers with 1 digit` \
            -e "s/^([0-9]{2})([:-])(.*)/\1\2     \3/"       `# Pad line numbers with 2 digits` \
            -e "s/^([0-9]{3})([:-])(.*)/\1\2    \3/"        `# Pad line numbers with 3 digits` \
            -e "s/^([0-9]{4})([:-])(.*)/\1\2   \3/"         `# Pad line numbers with 4 digits` \
            -e "s/^([0-9]{5})([:-])(.*)/\1\2  \3/"          `# Pad line numbers with 5 digits` \
            -e "s/^([0-9]+):(.*)/\x1b[1;31m\1\2\x1b[0;39m/" `# Make matched line red` \
            -e "s/^([0-9]+)-(.*)/\1\2/"                     `# Remove dash of unmatched line`
    done
}

# This function prints the major version of a string in the format XX.YY.ZZ
function major {
    # Split by "." and take the first element for the major version
    echo "$1" | cut -d. -f1
}

# This function prints the minor version of a string in the format XX.YY.ZZ
function minor {
    # Split by "." and take the second element for the minor version
    echo "$1" | cut -d. -f2
}

# This function activates the virtual environment and creates it if it doesn't exist yet
function activate_venv {
    if [[ -z "$LUNES_VENV_ACTIVATED" ]]; then
        # Create virtual environment if not exists
        if [[ ! -f ".venv/bin/activate" ]]; then
            echo "Creating virtual environment..." | print_info
            python3 -m venv .venv
            echo "✔ Created virtual environment" | print_success
        fi
        # Activate virtual environment
        # shellcheck disable=SC1091
        source .venv/bin/activate
        echo "✔ Activated virtual environment" | print_success
        LUNES_VENV_ACTIVATED=1
        export LUNES_VENV_ACTIVATED
    fi
}

# This function checks if the Lunes cms is installed
function require_installed {
    if [[ -z "$LUNES_CMS_INSTALLED" ]]; then
        # Activate virtual environment
        activate_venv
        echo "Checking if Lunes CMS is installed..." | print_info
        # Check if lunes-cms-cli is available in virtual environment
        if [[ ! -x "$(command -v lunes-cms-cli)" ]]; then
            echo -e "The Lunes CMS is not installed. Please install it with:\n"  | print_error
            echo -e "\t$(dirname "${BASH_SOURCE[0]}")/install.sh\n" | print_bold
            exit 1
        fi
        # Check if script is running in CircleCI context and set DEBUG=True if not
        if [[ -z "$CIRCLECI" ]] && [[ -z "$READTHEDOCS" ]]; then
            # Set debug mode
            LUNES_CMS_DEBUG=1
            export LUNES_CMS_DEBUG
            echo "Enabling debug mode..." | print_info
        else
            # Set dummy secret key
            LUNES_CMS_SECRET_KEY="dummy"
            export LUNES_CMS_SECRET_KEY
            echo "Setting dummy secret key..." | print_info
        fi
        # Use sqlite as database backend for local development
        LUNES_CMS_DB_BACKEND="sqlite"
        export LUNES_CMS_DB_BACKEND
        echo "Enabling SQLite database for local development..." | print_info
        # Check if lunes-cms-cli can be started
        if ! lunes-cms-cli > /dev/null; then
            echo -e "The Lunes CMS is could not be started due to the above error. Please install it again with:\n"  | print_error
            echo -e "\t$(dirname "${BASH_SOURCE[0]}")/install.sh\n" | print_bold
            exit 1
        fi
        echo "✔ Lunes CMS is installed" | print_success
        LUNES_CMS_INSTALLED=1
        export LUNES_CMS_INSTALLED
    fi
}

# This function migrates the database
function migrate_database {
    if [[ -z "$LUNES_DATABASE_MIGRATED" ]]; then
        require_installed
        echo "Migrating database..." | print_info
        # Generate migration files
        lunes-cms-cli makemigrations
        # Execute migrations
        lunes-cms-cli migrate
        echo "✔ Finished database migrations" | print_success
        LUNES_DATABASE_MIGRATED=1
        export LUNES_DATABASE_MIGRATED
    fi
}

# This function makes sure the database exists and is in the correct state
function require_database {
    if [[ -z "$LUNES_DATABASE" ]]; then
        require_installed
        # Check if database already exists
        if [ -f "${PACKAGE_DIR}/db.sqlite3" ]; then
            # Migrate database
            migrate_database
        else
            # Load test data
            bash "${DEV_TOOL_DIR}/load_test_data.sh"
        fi
        LUNES_DATABASE=1
        export LUNES_DATABASE
    fi
}

# This function shows a success message once the Lunes development server is running
function listen_for_devserver {
    until nc -z localhost "$LUNES_CMS_PORT"; do sleep 0.1; done
    echo "✔ Started Lunes CMS at http://localhost:${LUNES_CMS_PORT}" | print_success
}
