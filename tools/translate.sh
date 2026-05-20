#!/bin/bash

# This script can be used to re-generate the translation file and compile it. It is also executed in run.sh

# Import utility functions
# shellcheck source=./tools/_functions.sh
source "$(dirname "${BASH_SOURCE[0]}")/_functions.sh"

require_installed

# Change directory to make sure to ignore files in the venv
cd "${PACKAGE_DIR}" || exit 1

# Re-generating translation file
echo "Scanning Python and HTML source code and extracting translatable strings from it..." | print_info
lunes-cms-cli makemessages -l de
# Remove python-brace-format flags added by xgettext, as they vary between gettext versions and cause CI diffs
tmp=$(mktemp) && grep -v '^#, python-brace-format$' "locale/de/LC_MESSAGES/django.po" > "$tmp" && mv "$tmp" "locale/de/LC_MESSAGES/django.po"

# Ignore POT-Creation-Date of otherwise unchanged translation file
if git diff --shortstat locale/de/LC_MESSAGES/django.po | grep -q "1 file changed, 1 insertion(+), 1 deletion(-)"; then
    git checkout -- locale/de/LC_MESSAGES/django.po
fi

# Compile translation file
echo "Compiling translation file..." | print_info
lunes-cms-cli compilemessages

echo "✔ Translation process finished" | print_success
