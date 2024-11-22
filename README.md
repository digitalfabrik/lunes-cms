[![CircleCI](https://circleci.com/gh/digitalfabrik/lunes-cms.svg?style=shield)](https://circleci.com/gh/digitalfabrik/lunes-cms)
![Coverage](https://img.shields.io/codeclimate/coverage/digitalfabrik/lunes-cms)
[![Documentation Status](https://readthedocs.org/projects/lunes-cms/badge/?version=latest)](https://lunes-cms.readthedocs.io/en/latest/?badge=latest)
[![PyPi](https://img.shields.io/pypi/v/lunes-cms.svg)](https://pypi.org/project/lunes-cms/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Pylint](https://img.shields.io/badge/pylint-10.00-brightgreen)](https://www.pylint.org/)

# Lunes CMS
[![Logo](.github/logo.png) Lunes - Vocabulary for your profession.](https://www.lunes.app)

This is a Django 3 based content management system for the vocabulary trainer app Lunes, a project powered by [Tür an Tür – Digitalfabrik gGmbH](https://tuerantuer.de/digitalfabrik/).
The main goal is to develop an application which facilitates migrants to acquire technical and subject-specific vocabulary.
For more information please see our [GoVolunteer ad](https://translate.google.com/translate?hl=en&sl=de&tl=en&u=https%3A%2F%2Fgovolunteer.com%2Fde%2Fprojects%2Fehrenamtliche-entwickler-innen-fuer-vokabeltrainer).

## TL;DR

### Prerequisites

Following packages are required before installing the project (install them with your package manager):

* `python3.11` or higher
* `python3-pip`
* `python3-venv`
* `libpq-dev` to compile psycopg2
* `gettext` and `pcregrep` to use the translation features
* `ffmpeg` for audio processing

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

### Run development server

```
./tools/run.sh
```

* Go to your browser and open the URL `http://localhost:8080`
* Default user is "lunes" with password "lunes".

## Development documentation

For detailed instructions and the source code reference have a look at our documentation:

### <p align="center">:notebook: https://lunes-cms.rtfd.io</p>

## API documentation

The API usage documentation is available here:

### <p align="center">:iphone: https://lunes.tuerantuer.org/api/docs/</p>

## License

Copyright © 2020 [Tür an Tür - Digitalfabrik gGmbH](https://github.com/digitalfabrik) and [individual contributors](https://github.com/digitalfabrik/lunes-cms/graphs/contributors).
All rights reserved.

This project is licensed under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0), see [LICENSE](./LICENSE) and [NOTICE.md](./NOTICE.md).
