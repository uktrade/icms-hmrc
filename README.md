[![CircleCI](https://circleci.com/gh/uktrade/lite-hmrc.svg?style=svg)](https://circleci.com/gh/uktrade/lite-hmrc)

# Introduction
This project is meant for sending licence updates to HMRC and receiving usage reporting. Information like licence updates
and usage are exchanged as mail attachment between Lite and HMRC

Tasks are managed using this project: [Django Background Tasks](https://github.com/arteria/django-background-tasks/blob/master/docs/index.rst)

The entry point for configuring the tasks is defined here: `lite-hmrc/mail/apps.py`


# Build and Run
An `.env` file is expected at the root of project.

To make setup easy for those running in Docker there is a `docker.env` file provided which you can use in place of the `local.env` if you prefer.

Copy the template .env file: `cp local.env .env`

Or alternatively on Docker: `cp docker.env .env`

Copy the template local_settings.sample if required: `cp local_settings.sample local_settings.py`

if using local_settings.py remember to add this to your .env `DJANGO_SETTINGS_MODULE=local_settings`


### Running in Docker
To run in docker do the following
- Set up a `.env` file using `docker.env` as starting point (all the config given in `docker.env` should be sufficient to run containers and run tests)
- Start the containers: `docker-compose up --build`
- Initial setup (run once):
  - Run migrations: `make migrate`
  - Create super user: `make createsuperuser`
- Start the task runner: `make process-tasks`


### Running locally
- Configure .env file - Using local.env as a starting point:
  ```properties
  EMAIL_SMTP_PORT=587
  ```
- You may need to acquire additional credentials from [Vault](https://vault.ci.uktrade.digital/)
- To build and run a local Postfix [mail server](https://github.com/uktrade/mailserver)
- To initialise database: `PIPENV_DOTENV_LOCATION=.env pipenv run ./manage.py migrate`
- To create database superuser `PIPENV_DOTENV_LOCATION=.env pipenv run ./manage.py createsuperuser`
- To start the application: `PIPENV_DOTENV_LOCATION=.env pipenv run ./manage.py runserver`
- To start the task runner: `PIPENV_DOTENV_LOCATION=.env pipenv run ./manage.py process_tasks --log-std`
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

# Mailbox authentication

To authenticate with the mailboxes we have two separate authentication mechanisms

## Basic authentication

This authenticates using a username and password directly with the POP service.

## Modern authentication

For MS mailboxes the basic authentication is/has been removed as of 1st October 2022 and so we need to use modern authentication when accessing POP and SMTP accounts.

This uses OAuth and the full documentation is https://docs.microsoft.com/en-us/exchange/client-developer/legacy-protocols/how-to-authenticate-an-imap-pop-smtp-application-by-using-oauth.

The credentials need to be obtained from SRE who will provide them to you for the mailbox accounts that you require access to. We cannot do this ourselves as they are provided from the Azure infrastructure which we don't have access to.
