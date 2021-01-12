# About
This is a Django 2 based content management system for the vocabulary trainer app Lunes, a project powered by the Tür an Tür [Digital Factory](https://tuerantuer.de/digitalfabrik/). The main goal is to develop an application which facilitates migrants to acquire technical and subject-specific vocabulary. For more information please see our [GoVolunteer ad](https://translate.google.com/translate?hl=en&sl=de&tl=en&u=https%3A%2F%2Fgovolunteer.com%2Fde%2Fprojects%2Fehrenamtliche-entwickler-innen-fur-vokabeltrainer). 

# License
This project is licensed with the Apache 2.0 License.

# API
## List of disciplines
List available disciplines for learning.
### Request
```http
GET /api/disciplines/ HTTP/1.1
Host: lunes.tuerantuer.org
Content-Type: application/json
```
### Response
```javascript
[
    {
        "id": Integer,        // ID of discipline
        "title": String,      // title of discipline
        "description": String // description of discipline 
    },
    [...]                     // repeats for available disciplines
]
```

## List of training set
List training sets. If discipline ID is provided as a parameter, the list will return only training sets belonging to the discipline.
### Request
```http
GET /api/disciplines/[DISCIPLINE_ID] HTTP/1.1
Host: lunes.tuerantuer.org
Content-Type: application/json
```
### Response
```javascript
[
    {
        "id": Integer,    // ID of training set
        "title": String,  // title of discipline
        "details": String // details about training set 
    }
    [...]                 // repeats for available training sets
]
```
## List of documents
List of available documents. A document is an item to be learned and consists of an image, multiple correct answers, and other details. If training set ID is provided as a parameter, the list will return only documents belonging to the training set.
### Request
```http
GET /api/training_set/[TRAINING_SET_ID] HTTP/1.1
Host: lunes.tuerantuer.org
Content-Type: application/json
```
### Response
```javascript
[
    {
        "id": Integer,          // ID of training set
        "word": String,         // primary correct answer
        "article": String,      // article (german grammer) belonging to the item
        "image": String,        // URL to image
        "cropping": String,     // Image cropping information (X and Y offset + width and height?)
        "audio": String,        // URL to audio file
        "alternatives": {       // alternative correct answers
            "alt_word": String, // alternative correct answer for document
            "article": String,  // article (german grammer) belonging to the item
        }
    },
    [...]                   // repeats for available documents
]
```

# Development Setup
0. If you're on Windows, install the Windows Subsystem for Linux. Then execute `wsl bash` and continue with the commands below.
1. `git clone git@github.com:digitalfabrik/lunes-cms.git`
2. `cd lunes-cms`
3. `apt install python3-venv`
4. `python3 -m venv .venv`
5. `source .venv/bin/activate`
6. `python3 setup.py develop`
7. `python3 vocabulary-trainer migrate`
8. `python3 vocabulary-trainer createsuperuser`
9. `python3 vocabulary-trainer runserver`

# Usage
The API can simply be accessed via the root url or `/api`. </br>
In order to enter `/docs` successfully, it may be necessary to change the second line of the `index.html` file in `.venv/lib64/python3.9/site-packages/rest_framework_swagger/templates/rest_framework_swagger` from `{% load staticfiles %}` to `{% load static %}`.

# Production Deployment
1. `adduser vocabulary-trainer`
2. `git clone git@github.com:digitalfabrik/lunes-cms.git`
3. `cd lunes-cms`
4. `python3 setup.py install`
5. Change database settings in settings.py, for example to MySQL or Postgresql. After installation, usually find the settings.py in the /usr/lib/python3.X/site-packages/vocabulary-trainer
6. `vocabulary-trainer migrate`
7. `vocabulary-trainer collectstatic`
8. `systemctl start vocabulary-trainer.service`
9. Configure Apache2 or Nginx reverse proxy. See provided Apache2 example.
