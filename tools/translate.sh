#!/bin/bash

# This script can be used to re-generate the translation file and compile it. It is also executed in run.sh

# Import utility functions
# shellcheck source=./tools/_functions.sh
source "$(dirname "${BASH_SOURCE[0]}")/_functions.sh"

require_installed

# Change directory to make sure to ignore files in the venv
cd "${PACKAGE_DIR}" || exit 1

# Relative path from package directory
TRANSLATION_FILE="locale/de/LC_MESSAGES/django.po"

# Re-generating translation file
echo "Scanning Python and HTML source code and extracting translatable strings from it..." | print_info
lunes-cms-cli makemessages -l de --add-location file
# Remove python-brace-format flags added by xgettext, as they vary between gettext versions and cause CI diffs
tmp=$(mktemp) && grep -v '^#, python-brace-format$' "$TRANSLATION_FILE" > "$tmp" && mv "$tmp" "$TRANSLATION_FILE"

# Reset POT-Creation-Date to avoid git diffs of otherwise unchanged translation file
tmp=$(mktemp) && sed -E 's/^"POT-Creation-Date: [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}[+-][0-9]{4}\\n"$/"POT-Creation-Date: YEAR-MO-DA HO:MI+ZONE\\n"/' "$TRANSLATION_FILE" > "$tmp" && mv "$tmp" "$TRANSLATION_FILE"

# Skip compilation if --skip-compile option is given
if [[ "$*" != *"--skip-compile"* ]]; then
    # Compile translation file
    echo "Compiling translation file..." | print_info
    lunes-cms-cli compilemessages
fi

echo "✔ Translation process finished" | print_success
