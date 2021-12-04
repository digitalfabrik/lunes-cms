#!/bin/bash

#chmod +x dev-tools/build_documentation.sh
sphinx-apidoc --force --no-toc --module-first -o "sphinx" "src" "src/vocgui/migrations"
sphinx-build -j auto -W --keep-going sphinx docs