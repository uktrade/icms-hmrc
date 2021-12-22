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

#### Deploying to production

Important settings:

- SPIRE_ADDRESS: email address used by SPIRE system (legacy).
- SPIRE_INCOMING_EMAIL_ADDRESS: same as SPIRE_ADDRESS?
- HMRC_ADDRESS: email address used by HMRC / CHIEF to process licenses.
- LITE_HMRC_INTEGRATION_HAWK_KEY: part of Hawk authentication protocol.
- LITE_API_HAWK_KEY: part of Hawk authentication protocol.
- LITE_API_URL: base URL for API to send usage response data.
- EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_HOST, EMAIL_USE_TLS: default SMTP settings configured with EMAIL_URL environment variable.

#### Linting

- Code formatting and conventions

The python code formatter [Black](https://black.readthedocs.io/en/stable/) is used in this project.

To run it: `PIPENV_DOTENV_LOCATION=.env pipenv run black .`

To check the format `PIPENV_DOTENV_LOCATION=.env pipenv run black --check .`

- Code analysis tool

The tool `prospector` is used. To run it `pipenv run prospector .`

- Security and vulnerability linter

The tool 'bandit' is used. To run it `pipenv run bandit -r .`

#### Test

> NOTE: A task manager needs to be running locally if you are running E2E tests or similar. Check Procfile

The tests require a live postgres server. They will create a database called
`test_postgres` as part of the test run.

You may encounter `AssertionError: database connection isn't set to UTC` when running. To work around this set
`USE_TZ = False` in `conf/settings.py`.

Tests are located in `mail/tests`. To run all tests
`PIPENV_DOTENV_LOCATION=.env pipenv run ./manage.py test`
