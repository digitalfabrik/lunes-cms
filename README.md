[![GitHub issues](https://img.shields.io/github/issues/digitalfabrik/lunes-cms)](https://github.com/digitalfabrik/lunes-cms/issues)
[![GitHub pulls](https://img.shields.io/github/issues-pr/digitalfabrik/lunes-cms)](https://github.com/digitalfabrik/lunes-cms/pulls)
[![CircleCI](https://circleci.com/gh/digitalfabrik/lunes-cms.svg?style=svg)](https://circleci.com/gh/circleci/circleci-docs)
[![License](https://img.shields.io/github/license/digitalfabrik/lunes-cms)](https://opensource.org/licenses/Apache-2.0)
# Lunes CMS
[![Logo](.github/logo.png) Lunes - Vocabulary for your profession.](https://www.lunes.app)

This is a Django 2 based content management system for the vocabulary trainer app Lunes, a project powered by the Tür an Tür [Digital Factory](https://tuerantuer.de/digitalfabrik/). The main goal is to develop an application which facilitates migrants to acquire technical and subject-specific vocabulary. For more information please see our [GoVolunteer ad](https://translate.google.com/translate?hl=en&sl=de&tl=en&u=https%3A%2F%2Fgovolunteer.com%2Fde%2Fprojects%2Fehrenamtliche-entwickler-innen-fur-vokabeltrainer). 

# License
This project is licensed with the Apache 2.0 License.

# API
Further documentation can be accessed [here](https://lunes.tuerantuer.org/redoc/).

## Authentication
Generally, all endpoints are free to use and hence are not secured. However, this doesn't apply for group-specific requests e.g. `/api/group_info` (see below). Within the Lunes CMS it is possible to create API-Keys for a specific group. In order to fetch data of a group, it is necessary to include the following authorization header in the request:
```json
{"Authorization": "Api-Key <API_KEY>"}
```
Authorization is needed every time when content is accessed that was not created by Lunes administrators.

## Group information
List available information of a user group. A valid API-Key is required. There is no need to pass a group id or similar, the returned queryset is filtered by the delivered API-Key.

### Request
```http
GET /api/group_info HTTP/1.1
Host: lunes.tuerantuer.org
Content-Type: application/json
```

#### Response
```javascript
[
    {
        "id": Integer,                          // group id
        "name": String,                         // name of user group
        "icon": String,                         // URL to image
        "total_discipline_children": Integer,   // number of disciplines of user group
    }
]
```

## List of disciplines
List available disciplines for learning.

### Disciplines filtered by group id
This endpoint displays all child disciplines for a given group id. A valid API-Key is required.

#### Request
```http
GET /api/disciplines_by_group/[GROUP_ID] HTTP/1.1
Host: lunes.tuerantuer.org
Content-Type: application/json
```

#### Response
```javascript
[
    {
        "id": Integer,                  // ID of discipline
        "title": String,                // title of discipline
        "description": String,          // description of discipline 
        "icon": String,                 // URL to image
        "created_by": Integer           // Creator group id, null if created by admin 
        "total_training_sets": Integer  // # of training sets
        "total_discipline_children": Integer // # of child disciplines
    },
    [...]   // repeats for available disciplines
]
```

### Disciplines filtered by levels
This endpoint displays all child disciplines for a given discipline id. If no id is given, all root disciplines will be returned. A valid API-Key may be required.

#### Request
```http
GET /api/disciplines_by_level/ HTTP/1.1
Host: lunes.tuerantuer.org
Content-Type: application/json
```
The default endpoint delivers all root disciplines created by Lunes administrators. Optionally, a discipline id can be passed as follows:
```http
GET /api/disciplines_by_level/[DISCIPLINE_ID] HTTP/1.1
Host: lunes.tuerantuer.org
Content-Type: application/json
```
If the passed discipline id belongs to a custom user group (not to the Lunes admin team), a API-Key is required.

#### Response
```javascript
[
    {
        "id": Integer,                  // ID of discipline
        "title": String,                // title of discipline
        "description": String,          // description of discipline 
        "icon": String,                 // URL to image
        "created_by": Integer           // Creator group id, null if created by admin 
        "total_training_sets": Integer  // # of training sets
        "total_discipline_children": Integer // # of child disciplines
    },
    [...]   // repeats for available disciplines
]
```


### Disciplines without child elements (deprecated)
This endpoint only delivers disciplines that do not have any child elements. Generally, it is advised to use the newer version of this endpoint (see above). However, to keep Lunes functioning for people who haven't installed the recent update, this feature is still available.

#### Request
```http
GET /api/disciplines/ HTTP/1.1
Host: lunes.tuerantuer.org
Content-Type: application/json
```
The default endpoint delivers all disciplines created by Lunes administrators.

#### Response
```javascript
[
    {
        "id": Integer,                  // ID of discipline
        "title": String,                // title of discipline
        "description": String,          // description of discipline 
        "icon": String,                 // URL to image
        "created_by": Integer           // Creator group id, null if created by admin 
        "total_training_sets": Integer  // # of training sets
        "total_discipline_children": Integer // # of child disciplines
    },
    [...]   // repeats for available disciplines
]
```

## List of training set
List training sets. If discipline ID is provided as a parameter, the list will return only training sets belonging to the discipline. A valid API-Key may be required.
### Request
```http
GET /api/training_set/[DISCIPLINE_ID] HTTP/1.1
Host: lunes.tuerantuer.org
Content-Type: application/json
```
### Response
```javascript
[
    {
        "id": Integer,             // ID of training set
        "title": String,           // title of discipline
        "details": String,         // details about training set 
        "icon": String,            // URL to image
        "total_documents": Integer // # of documents
    }
    [...]   // repeats for available training sets
]
```

## List of documents
List of available documents. A document is an item to be learned and consists of an image, multiple correct answers, and other details. If training set ID is provided as a parameter, the list will return only documents belonging to the training set. A valid API-Key may be required.
### Request
```http
GET /api/documents/[TRAINING_SET_ID] HTTP/1.1
Host: lunes.tuerantuer.org
Content-Type: application/json
```
### Response
```javascript
[
    {
        "id": Integer,              // ID of training set
        "word": String,             // primary correct answer
        "article": Integer,         // ID of article (german grammar) belonging to the item (1:Der, 2:Die, 3:Das, 4:Die (Plural))
        "audio": String,            // URL to (converted) audio file
        "word_type": String,        // Word type of document: Nomen, Verb, Adjektiv
        "alternatives": [
            {
                "alt_word": String,         // Alternative word
                "article": Integer,         // ID of article (german grammer) belonging to the item (1:Der, 2:Die, 3:Das, 4:Die (Plural))
            },
            [...]   // repeats for available alternatives
        ],
        "document_image": [
            {
                "id": Integer,  //image id
                "image": String //URL to image
            },
            [...]   // repeats for available images
        ]
    },
    [...]   // repeats for available documents
]
```

# Development Setup
This project runs on Django – if you're new to Django it may be worth
checking out [Django's getting started guide](https://www.djangoproject.com/start/).

Here's how to get the site running on your machine.

1. Get into a Unix-like environment
    - If you're on Windows, install the Windows Subsystem for Linux. Then execute `wsl bash` and continue with the commands below.
    - If you're already on Linux/Mac, no action needed.
2. Clone the repository: `git clone git@github.com:digitalfabrik/lunes-cms.git`
3. Move into the direcotry: `cd lunes-cms`
4. Set up virtual environment of choice with a current `pip` and `setuptools` version. For example (using Debian):
    - `apt install python3-venv`
    - `python3 -m venv .venv`
    - `source .venv/bin/activate`
    - `pip install -U pip setuptools`
    - `pip install wheel`
5. Install system dependencies: `cat requirements.system | xargs sudo apt-get install`
6. Install project dependencies: `python3 setup.py develop`
7. Set up Django and run the development server:
    - `vocabulary-trainer migrate`
    - `vocabulary-trainer createsuperuser`
    - `vocabulary-trainer runserver`

Now that you've gotten everything set up, to run the development server in
the future, all you'll need to do is activate your virtual environment
(e.g. via `source .venv/bin/activate` if you use the instructions above, or
`pipenv shell` if you're using pipenv) and call `runserver` like in the
last command above.

# Usage
The API can simply be accessed via the root url or `/api`.

Further Documentation can be found by accessing `/redoc` or `/swagger`.


# Production Deployment
1. `adduser vocabulary-trainer`
2. `git clone git@github.com:digitalfabrik/lunes-cms.git`
3. `cd lunes-cms`
4. `python3 setup.py install`
5. `cat requirements.system | xargs sudo apt-get`
6. Change database settings in settings.py, for example to MySQL or Postgresql. After installation, usually find the settings.py in the /usr/lib/python3.X/site-packages/vocabulary-trainer
7. `vocabulary-trainer migrate`
8. `vocabulary-trainer collectstatic`
9. `systemctl start vocabulary-trainer.service`
10. Configure Apache2 or Nginx reverse proxy. See provided Apache2 example.
