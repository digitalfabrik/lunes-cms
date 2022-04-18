[![CircleCI](https://circleci.com/gh/digitalfabrik/lunes-cms.svg?style=shield)](https://circleci.com/gh/digitalfabrik/lunes-cms)
[![License](https://img.shields.io/github/license/digitalfabrik/lunes-cms)](https://opensource.org/licenses/Apache-2.0)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
# Lunes CMS
[![Logo](.github/logo.png) Lunes - Vocabulary for your profession.](https://www.lunes.app)

This is a Django 3 based content management system for the vocabulary trainer app Lunes, a project powered by the Tür an Tür [Digital Factory](https://tuerantuer.de/digitalfabrik/).
The main goal is to develop an application which facilitates migrants to acquire technical and subject-specific vocabulary.
For more information please see our [GoVolunteer ad](https://translate.google.com/translate?hl=en&sl=de&tl=en&u=https%3A%2F%2Fgovolunteer.com%2Fde%2Fprojects%2Fehrenamtliche-entwickler-innen-fur-vokabeltrainer).

## TL;DR

### Prerequisites

Following packages are required before installing the project (install them with your package manager):

* python3.8 or higher
* python3-pip
* gettext and pcregrep to use the translation features
* ffmpeg for audio processing

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

## API

Further documentation can be accessed [here](https://lunes.tuerantuer.org/redoc/).

### Authentication
Generally, all endpoints are free to use and hence are not secured. However, this doesn't apply for group-specific requests e.g. `/api/group_info` (see below). Within the Lunes CMS it is possible to create API-Keys for a specific group. In order to fetch data of a group, it is necessary to include the following authorization header in the request:
```json
{"Authorization": "Api-Key <API_KEY>"}
```
Authorization is needed every time when content is accessed that was not created by Lunes administrators.

### Group information
List available information of a user group. A valid API-Key is required. There is no need to pass a group id or similar, the returned queryset is filtered by the delivered API-Key.

#### Request
```http
GET /api/group_info HTTP/1.1
Host: lunes.tuerantuer.org
Content-Type: application/json
```

##### Response
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

### List of disciplines
List available disciplines for learning.

#### Disciplines filtered by group id
This endpoint displays all child disciplines for a given group id. A valid API-Key is required.

##### Request
```http
GET /api/disciplines_by_group/[GROUP_ID] HTTP/1.1
Host: lunes.tuerantuer.org
Content-Type: application/json
```

##### Response
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
        "nested_training_sets": List[Integer] // training set ids of discipline and its child elements
    },
    [...]   // repeats for available disciplines
]
```

#### Disciplines filtered by levels
This endpoint displays all child disciplines for a given discipline id. If no id is given, all root disciplines will be returned. A valid API-Key may be required.

##### Request
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

##### Response
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
        "nested_training_sets": List[Integer] // training set ids of discipline and its child elements
    },
    [...]   // repeats for available disciplines
]
```


#### All disciplines
This endpoint delivers all disciplines, either all global disciplines or filtered by the given API key.
A single record can be retrieved by appending the id of the requested discipline.

##### Request
```http
GET /api/disciplines/ HTTP/1.1
Host: lunes.tuerantuer.org
Content-Type: application/json
```
The default endpoint delivers all disciplines created by Lunes administrators.

##### Response
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
        "nested_training_sets": List[Integer] // training set ids of discipline and its child elements
    },
    [...]   // repeats for available disciplines
]
```

### List of training set
List training sets. If discipline ID is provided as a parameter, the list will return only training sets belonging to the discipline. A valid API-Key may be required.
#### Request
```http
GET /api/training_set/[DISCIPLINE_ID] HTTP/1.1
Host: lunes.tuerantuer.org
Content-Type: application/json
```
#### Response
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

### List of documents
List of available documents. A document is an item to be learned and consists of an image, multiple correct answers, and other details. If training set ID is provided as a parameter, the list will return only documents belonging to the training set. A valid API-Key may be required.

#### List of documents by training set
Get all documents that belong to a given training set

##### Request
```http
GET /api/documents/[TRAINING_SET_ID] HTTP/1.1
Host: lunes.tuerantuer.org
Content-Type: application/json
```
##### Response
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
                "article": Integer,         // ID of article (german grammar) belonging to the item (1:Der, 2:Die, 3:Das, 4:Die (Plural))
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

#### All documents
Get the list of all documents or retrieve a single record by appending the id of the word.

##### Request
```http
GET /api/words/HTTP/1.1
Host: lunes.tuerantuer.org
Content-Type: application/json
```
##### Response
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
                "article": Integer,         // ID of article (german grammar) belonging to the item (1:Der, 2:Die, 3:Das, 4:Die (Plural))
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
