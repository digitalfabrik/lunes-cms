#!/bin/bash

# This script installs the CMS in a local virtual environment

# Import utility functions
# shellcheck source=./tools/_functions.sh
source "$(dirname "${BASH_SOURCE[0]}")/_functions.sh"

echo "Checking system requirements..." | print_info
# Check if requirements are satisfied

# Define the required python version
required_python_version="11"
if [[ ! -x "$(command -v python3)" ]]; then  echo "Python3 is not installed. Please install version 3.${required_python_version} or later manually and run this script again."  | print_error
    exit 1
fi
python_version=$(python3 --version | cut -d" " -f2)
# Check if required npm version is installed
if [[ $(minor "$python_version") -lt "$required_python_version" ]]; then
    echo "Python version 3.${required_python_version} or higher is required, but version ${python_version} is installed. Please install a recent version manually and run this script again."  | print_error
    exit 1
fi
if [[ ! -x "$(command -v pip3)" ]]; then
    echo "Pip for Python3 is not installed. Please install python3-pip manually and run this script again."  | print_error
    exit 1
fi
# Check if uv is installed
if [[ ! -x "$(command -v uv)" ]]; then
    echo -e "uv is not installed. Please install it manually and run this script again:\n" | print_error
    echo -e "\thttps://docs.astral.sh/uv/getting-started/installation/\n" | print_bold
    exit 1
fi
# Check if prerequisite for psycopg2 is installed
if [[ ! -x "$(command -v pg_config)" ]]; then
    echo "The command pg_config is not available. Please install libpq-dev manually and run this script again."  | print_error
    exit 1
fi
# Check if nc (netcat) is installed
if [[ ! -x "$(command -v nc)" ]]; then
    echo "Netcat is not installed. Please install it manually and run this script again."  | print_error
    exit 1
fi
# Check if GNU gettext tools are installed
if [[ ! -x "$(command -v msguniq)" ]]; then
    echo "GNU gettext tools are not installed. Please install gettext manually and run this script again."  | print_error
    exit 1
fi
# Check if pcregrep is installed
if [[ ! -x "$(command -v pcregrep)" ]]; then
    echo "PCRE grep is not installed. Please install pcregrep manually and run this script again."  | print_error
    exit 1
fi
# Check if ffmpeg is installed
if [[ ! -x "$(command -v ffmpeg)" ]]; then
    echo "FFmpeg is not installed. Please install ffmpeg manually and run this script again."  | print_error
    exit 1
fi
# Check if npm is installed
if [[ ! -x "$(command -v npm)" ]]; then
    echo "npm is not installed. Please install Node.js and npm manually and run this script again."  | print_error
    exit 1
fi
echo "✔ All system requirements are satisfied" | print_success

# Check if the --clean option is given
if [[ "$*" == *"--clean"* ]]; then
    echo "Removing installed dependencies..." | print_info
    # Report deleted files but only the explicitly deleted directories
    rm -rfv .venv | grep -E -- "'.venv'" || true
fi

# Activate virtual environment
activate_venv

# Install pinned dependencies from the lock file
echo "Installing Lunes CMS including its python dependencies..." | print_info
uv sync --extra dev

# Install node dependencies
echo "Installing Node.js dependencies..." | print_info
npm install

# Install pre-commit-hooks if --pre-commit option is given
if [[ "$*" == *"--pre-commit"* ]]; then
    echo "Installing pre-commit hooks..." | print_info
    # Install pre-commit hooks
    pre-commit install
    echo "✔ Installed pre-commit hooks" | print_success
fi

echo -e "\n✔ Lunes CMS was successfully installed 😻" | print_success
echo -e "Use the following command to start the development server:\n" | print_info
echo -e "\t$(dirname "${BASH_SOURCE[0]}")/run.sh\n" | print_bold
