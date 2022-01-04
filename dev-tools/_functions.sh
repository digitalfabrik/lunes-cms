#!/bin/bash

# This file contains utility functions which can be used in the dev-tools.

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