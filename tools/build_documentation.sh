#!/bin/bash

# Script to generate and build documentation.

DOC_DIR="docs"
DOC_DIST_DIR="${DOC_DIR}/dist"
DOC_SRC_DIR="${DOC_DIR}/src"
DOC_SRC_REF_DIR="${DOC_SRC_DIR}/ref"

# Import utility functions
# shellcheck source=./tools/_functions.sh
source "$(dirname "${BASH_SOURCE[0]}")/_functions.sh"

require_installed

# This function suggests the clean parameter
function suggest_clean_parameter  {
    echo -e "\nIf you think the above error is not your fault, try a clean documentation build with:\n" | print_info
    echo -e "\t${0} --clean\n" | print_bold
}

# remove stale doc files
if [[ "$*" == *"--clean"* ]]; then
    echo "Removing temporary documentation files..." | print_info
    rm -rf "${DOC_DIST_DIR}" "${DOC_SRC_REF_DIR}"
elif [[ -z "$CIRCLECI" ]]; then
    # If the script is neither running on CircleCI, nor a clean build and failing anyway, trap to suggest the --clean parameter
    trap 'suggest_clean_parameter' ERR
fi

# Generate .rst files
echo -e "Scanning Python source code and generating reStructuredText files from it..." | print_info
sphinx-apidoc --no-toc --module-first -o "${DOC_SRC_REF_DIR}" "${PACKAGE_DIR}" "${PACKAGE_DIR}/cms/migrations" "${PACKAGE_DIR}/cmsv2/views/*.py"

# Modify .rst files to remove unnecessary submodule- & subpackage-titles
# At first, the 'find'-command returns all .rst files in the sphinx directory
# The sed pattern replacement is divided into five stages explained below:
# Use different sed syntax for macOS (BSD) vs Linux (GNU)
if [[ "$OSTYPE" == "darwin"* ]]; then
    SED_INPLACE="sed -i ''"
else
    SED_INPLACE="sed -i"
fi

# shellcheck disable=SC2086
find "${DOC_SRC_REF_DIR}" -type f -name "*.rst" -print0 | xargs -0 --no-run-if-empty $SED_INPLACE \
    -e '/Submodules\|Subpackages/{N;d;}' `# Remove Sub-Headings including their following lines` \
    -e 's/\( module\| package\)//' `# Remove module & package strings at the end of headings` \
    -e '/^[^ ]\+$/s/\(.*\.\)\?\([^\.]\+\)/\u\2/' `# Remove module path in headings (separated by dots) and make first letter uppercase` \
    -e '/^[^ ]\+$/s/\\_\([a-z]\)/ \u\1/g' `# Replace \_ with spaces in headings and make following letter uppercase` \
    -e 's/Cms/CMS/g;s/Api/API/g' # Make specific keywords uppercase

# Copy changelog to documentation files
cp CHANGELOG.md ${DOC_SRC_DIR}/changelog.rst

# Add changelog heading
$SED_INPLACE '1s/^/Changelog\n=========\n\n/' ${DOC_SRC_DIR}/changelog.rst

# Convert markdown-links to ReStructuredText-links
# shellcheck disable=SC2016
$SED_INPLACE -E 's|\[#([0-9]+)\](https://github\.com/digitalfabrik/lunes-cms/issues/([0-9]+))|:github:`#\1 <issues/\1>`|' ${DOC_SRC_DIR}/changelog.rst


if [[ -z "$READTHEDOCS" ]]; then
    # Build documentation
    echo -e "Generating documentation from reStructuredText files..." | print_info
    sphinx-build -j auto -W --keep-going "${DOC_SRC_DIR}" "${DOC_DIST_DIR}"
    # Remove temporary changelog file
    rm "${DOC_SRC_DIR}/changelog.rst"
    echo -e "✔ Documentation build complete 😻" | print_success
    if [[ -z "$CIRCLECI" ]]; then
        echo -e "Open the following file in your browser to view the result:\n" | print_info
        echo -e "\tfile://${BASE_DIR}/${DOC_DIST_DIR}/index.html\n" | print_bold
    fi
else
    # Skip HTML build on Read the Docs because it's done in a separate build step
    echo -e "✔ Generated rst files from source code" | print_success
fi
