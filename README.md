# About
This is a Django 2 based content management system for the vocabulary trainer app Lunes, a project powered by the Tür an Tür [Digital Factory](https://tuerantuer.de/digitalfabrik/). The main goal is to develop an application which facilitates migrants to acquire technical and subject-specific vocabulary. For more information please see our [GoVolunteer ad](https://translate.google.com/translate?hl=en&sl=de&tl=en&u=https%3A%2F%2Fgovolunteer.com%2Fde%2Fprojects%2Fehrenamtliche-entwickler-innen-fur-vokabeltrainer). 

# License
This project is licensed with the Apache 2.0 License.

# API
Further documentation can be accessed [here](https://lunes.tuerantuer.org/redoc/).
## List of disciplines
List available disciplines for learning.
### Request
```http
GET /api/disciplines/ HTTP/1.1
Host: lunes.tuerantuer.org
Content-Type: application/json
```
The default endpoint delivers all disciplines created by Lunes administrators. Optionally, group ids can be passed as well (multiple ids devided by `&`):
```http
GET /api/disciplines/[[GROUP_ID]&[GROUP_ID]&[...]] HTTP/1.1
Host: lunes.tuerantuer.org
Content-Type: application/json
```
The request will return all disciplines either created by Lunes administrators or by one of the passed user groups.

### Response
```javascript
[
    {
        "id": Integer,                  // ID of discipline
        "title": String,                // title of discipline
        "description": String,          // description of discipline 
        "icon": String,                 // URL to image
        "created_by": Integer           // Creator group id, null if created by admin 
        "total_training_sets": Integer  // # of training sets
    },
    [...]   // repeats for available disciplines
]
```

## List of training set
List training sets. If discipline ID is provided as a parameter, the list will return only training sets belonging to the discipline.
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
List of available documents. A document is an item to be learned and consists of an image, multiple correct answers, and other details. If training set ID is provided as a parameter, the list will return only documents belonging to the training set.
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
4. Set up virtual environment of choice. For example (using Debian):
    - `apt install python3-venv`
    - `python3 -m venv .venv`
    - `source .venv/bin/activate`
5. Install project dependencies: `python3 setup.py develop`
6. Install system dependencies: `cat requirements.system | xargs sudo apt-get install`
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
