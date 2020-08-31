# About
This is a Django 2 based visual word trainer for small training sets of technical terms.

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
