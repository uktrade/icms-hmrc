[![CircleCI](https://circleci.com/gh/uktrade/lite-hmrc.svg?style=svg)](https://circleci.com/gh/uktrade/lite-hmrc)

## Introduction
This project is meant for sending licence updates to HMRC and receiving usage reporting. Information like licence updates
and usage are exchanged as mail attachment between Lite and HMRC

#### Build and Run


##### Without Docker
- To build and run a local Postfix [mail server](https://github.com/uktrade/mailserver)
- To initilize database
`PIPENV_DOTENV_LOCATION=.env pipenv run ./manage.py migrate`
- To create database superuser `PIPENV_DOTENV_LOCATION=.env pipenv run ./manage.py createsuperuser`
- To start the application
`PIPENV_DOTENV_LOCATION=.env pipenv run ./manage.py runserver`

##### With Docker

An `.env` file is expected at the root of project. An example provided below
```properties
DATABASE_URL=postgresql://postgres:password@lite-hmrc-postgres:5432/postgres
DJANGO_SECRET_KEY='DJANGO_SECRET_KEY'
EMAIL_PASSWORD=password
EMAIL_HOSTNAME=lite-hmrc-ditmail
EMAIL_USER=username
EMAIL_POP3_PORT=995
EMAIL_SMTP_PORT=587
TIME_TESTS=true
LOCK_INTERVAL=120
SPIRE_ADDRESS=test@spire.com
HMRC_ADDRESS=HMRC
```
- check out [mailserver](https://github.com/uktrade/mailserver) to a local folder
has the same parent folder of this repo
- `docker-compose up --build -d`

if it is the first time building the local environment, a database migration is required to be carried out.
Run the following command

- `docker exec -it lite-hmrc-intg pipenv run ./manage.py migrate`
- `docker exec -it lite-hmrc-intg pipenv run ./manage.py createsuperuser`

#### Linting

- Code formatting and conventions

[Black](https://black.readthedocs.io/en/stable/) and isort are used in this project to enforce a consistent code style.

Apply formatting:

    export PIPENV_DOTENV_LOCATION=.env
    pipenv run black .
    pipenv run isort .

Check formatting:

    export PIPENV_DOTENV_LOCATION=.env
    pipenv run black --check .
    pipenv run isort --check --diff .

- Code analysis tool

The tool `prospector` is used. To run it `pipenv run prospector .`

- Security and vulnerability linter

The tool 'bandit' is used. To run it `pipenv run bandit -r .`

#### Git Hub pre-commit setup
- Install pre-commit (e.g MAC pip install pre-commit)
- pre-commit install
* run following to scan all files for issues
  - pre-commit run --all-files

#### Test

> NOTE: A task manager needs to be running locally if you are running E2E tests or similar. Check Procfile

The tests require a live postgres server. They will create a database called
`test_postgres` as part of the test run.

You may encounter `AssertionError: database connection isn't set to UTC` when running. To work around this set
`USE_TZ = False` in `conf/settings.py`.

Tests are located in `mail/tests`. To run all tests
`PIPENV_DOTENV_LOCATION=.env pipenv run ./manage.py test`
