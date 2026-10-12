[![CircleCI](https://circleci.com/gh/digitalfabrik/lunes-cms.svg?style=shield)](https://circleci.com/gh/digitalfabrik/lunes-cms)
[![Documentation Status](https://readthedocs.org/projects/lunes-cms/badge/?version=latest)](https://lunes-cms.readthedocs.io/en/latest/?badge=latest)
[![PyPi](https://img.shields.io/pypi/v/lunes-cms.svg)](https://pypi.org/project/lunes-cms/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/pylint-dev/pylint)

# Lunes CMS
[![Logo](.github/logo.png) Lunes - Vocabulary for your profession.](https://www.lunes.app)

This is a Django 5 based content management system for the vocabulary trainer app Lunes, a project powered by [Tür an Tür – Digitalfabrik gGmbH](https://tuerantuer.de/digitalfabrik/).
The main goal is to develop an application which facilitates migrants to acquire technical and subject-specific vocabulary.
Outside contributions to our project are always welcome. For more information on that topic please read our [wiki page](https://wiki.tuerantuer.org/ehrenamt).

## TL;DR

### Prerequisites

The following packages are required before installing the project (install them with your package manager):

* `python3.11` or higher
* `python3-pip`
* `python3-venv`
* [`uv`](https://docs.astral.sh/uv/getting-started/installation/) to install the pinned/locked python dependencies
* `libpq-dev`, `python3-dev` and `build-essential` to compile psycopg2
* `netcat-openbsd` used by the dev scripts to detect when the server is up
* `gettext` and `pcregrep` to use the translation features
* `ffmpeg` for audio processing
* `nodejs` and `npm` to build the TypeScript frontend

E.g. on Debian-based distributions, use:

```
cat requirements.system | xargs sudo apt-get install
```

### Installation

```
git clone git@github.com:digitalfabrik/lunes-cms.git
cd lunes-cms
./tools/install.sh
```

### IntelliJ with Python virtual environment

Some IntelliJ versions do not activate Python virtual environment automatically.
In this case you can use IntelliJ together with the [direnv plugin](https://plugins.jetbrains.com/plugin/15285-direnv-integration) and the provided `.envrc`.
It automatically activates the Python virtual environment (`.venv`) when opening the project.
* Note: The direnv binary has to be installed on your system.

### Run development server

```bash
./tools/run.sh
```

* Go to your browser and open the URL `http://localhost:8080`
* Default user is "lunes" with password "lunes".

## Development documentation

For detailed instructions and the source code reference have a look at our documentation:

### <p align="center">:notebook: https://lunes-cms.rtfd.io</p>

## API documentation

The API usage documentation is available here:

### <p align="center">:iphone: https://lunes.tuerantuer.org/api/v2/</p>

## User manual

Our user manual can be found here:

### <p align="center">:open_book: https://digitalfabrik.github.io/lunes-cms/</p>

## License

Copyright © 2026 [Tür an Tür - Digitalfabrik gGmbH](https://github.com/digitalfabrik) and [individual contributors](https://github.com/digitalfabrik/lunes-cms/graphs/contributors).
All rights reserved.

This project is licensed under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0), see [LICENSE](./LICENSE) and [NOTICE.md](./NOTICE.md).
