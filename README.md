[![CircleCI](https://circleci.com/gh/uktrade/lite-hmrc.svg?style=svg)](https://circleci.com/gh/uktrade/lite-hmrc)

# Introduction
This project is meant for sending licence updates to HMRC and receiving usage reporting. Information like licence updates
and usage are exchanged as mail attachment between Lite and HMRC

# Build and Run
An `.env` file is expected at the root of project.

Copy the template .env file: `cp local.env .env`

### Running in Docker
To run in docker do the following
- Configure .env file - Using local.env as a starting point:
  ```properties
  DATABASE_URL=postgres://postgres:password@lite-hmrc-postgres:5432/postgres
  MAILHOG_URL=http://mailhog:8025
  EMAIL_HOSTNAME=mailhog
  ```
- Start the containers: `docker-compose up --build`
- Initial setup (run once):
  - Run migrations: `make migrate`
  - Create super user: `make createsuperuser`


### Running locally
- Configure .env file - Using local.env as a starting point:
  ```properties
  EMAIL_SMTP_PORT=587
  ```
- To build and run a local Postfix [mail server](https://github.com/uktrade/mailserver)
- To initilize database
`PIPENV_DOTENV_LOCATION=.env pipenv run ./manage.py migrate`
- To create database superuser `PIPENV_DOTENV_LOCATION=.env pipenv run ./manage.py createsuperuser`
- To start the application
`PIPENV_DOTENV_LOCATION=.env pipenv run ./manage.py runserver`
- check out [mailserver](https://github.com/uktrade/mailserver) to a local folder
has the same parent folder of this repo
- `docker-compose up --build -d`

**To check either setup is working correctly navigate to the following url:** `http://localhost:8000/healthcheck/`

# Testing
Tests are located in `mail/tests`.

### To run the tests in a container:
- Ensure correct environment variables are set (see Running in Docker section)
- Run the containers (to ensure MailHog is running): `docker-compose up`
- Run this command: `make test-in`

### To run the tests locally:
- Ensure correct environment variables are set (see Running locally section)
- Run this command: `make test`

> NOTE: A task manager needs to be running locally if you are running E2E tests or similar. Check Procfile

The tests require a live postgres server. They will create a database called
`test_postgres` as part of the test run.

You may encounter `AssertionError: database connection isn't set to UTC` when running. To work around this set
`USE_TZ = False` in `conf/settings.py`.

# Linting

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

# Git Hub pre-commit setup
- Install pre-commit (e.g MAC `pip install pre-commit`)
- `pre-commit install`
* run following to scan all files for issues
  - `pre-commit run --all-files`
