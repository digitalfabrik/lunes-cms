# About
This is a Django 2 based visual word trainer for small training sets of technical terms.

# Development Setup
1. `git clone git@github.com:digitalfabrik/visual-vocabulary-trainer.git`
2. `cd visual-vocabulary-trainer`
3. `apt install python3-venv`
4. `python3 -m venv .venv`
5. `source .venv/bin/activate`
6. `python3 setup.py develop`
7. `manage.py migrate`
8. `manage.py createsuperuser`
9. `manage.py runserver`

# Production Deployment
