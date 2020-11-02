# About
This is a Django 2 based content management system for the vocabulary trainer app Lunes. This is a project powered by the Tür an Tür [Digital Factory](https://tuerantuer.de/digitalfabrik/).

# License
This project is licensed with the Apache 2.0 License.

# Development Setup
0. If you're on Windows, install the Windows Subsystem for Linux. Then execute `wsl bash` and continue with the commands below.
1. `git clone git@github.com:digitalfabrik/visual-vocabulary-trainer.git`
2. `cd visual-vocabulary-trainer`
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
2. `git clone git@github.com:digitalfabrik/visual-vocabulary-trainer.git`
3. `cd visual-vocabulary-trainer`
4. `python3 setup.py install`
5. Change database settings in settings.py, for example to MySQL or Postgresql. After installation, usually find the settings.py in the /usr/lib/python3.X/site-packages/vocabulary-trainer
6. `vocabulary-trainer migrate`
7. `vocabulary-trainer collectstatic`
8. `systemctl start vocabulary-trainer.service`
9. Configure Apache2 or Nginx reverse proxy. See provided Apache2 example.
