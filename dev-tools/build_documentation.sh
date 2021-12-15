#!/bin/bash

# Script to generate and build documentation. Eventually, you need to run
# chmod +x dev-tools/build_documentation.sh first in order to have
# executable rights

DOC_DIR="docs"
SPHINX_DIR="sphinx"
SPHINX_APIDOC_DIR="sphinx/ref"

# Import utility functions
# shellcheck source=./dev-tools/_functions.sh
source "$(dirname "${BASH_SOURCE[0]}")/_functions.sh"

# remove stale doc files
if [[ "$*" == *"--clean"* ]]; then
    echo "Removing temporary documentation files..." | print_info
    rm -rf ${DOC_DIR} ${SPHINX_APIDOC_DIR}
fi

# Generate .rst files
echo -e "Scanning Python source code and generating reStructuredText files from it..." | print_info
sphinx-apidoc --no-toc --module-first -o ${SPHINX_APIDOC_DIR} "src" "src/vocgui/migrations"

# Modify .rst files to remove unnecessary submodule- & subpackage-titles
# Example: "integreat_cms.cms.models.push_notifications.push_notification_translation module" becomes "Push Notification Translation"
# At first, the 'find'-command returns all .rst files in the sphinx directory
# The sed pattern replacement is divided into five stages explained below:
find ${SPHINX_DIR}/${SPHINX_APIDOC_EXT_DIR} -type f -name "*.rst" -print0 | xargs -0 --no-run-if-empty sed --in-place \
    -e '/Submodules\|Subpackages/{N;d;}' `# Remove Sub-Headings including their following lines` \
    -e 's/\( module\| package\)//' `# Remove module & package strings at the end of headings` \
    -e '/^[^ ]\+$/s/\(.*\.\)\?\([^\.]\+\)/\u\2/' `# Remove module path in headings (separated by dots) and make first letter uppercase` \
    -e '/^[^ ]\+$/s/\\_\([a-z]\)/ \u\1/g' `# Replace \_ with spaces in headings and make following letter uppercase`

# Build documentation
echo -e "Generating documentation from reStructuredText files..." | print_info
sphinx-build -j auto -W --keep-going sphinx docs

echo -e "✔ Documentation build complete 😻" | print_success
