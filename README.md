[![CircleCI](https://circleci.com/gh/uktrade/icms-hmrc.svg?style=svg)](https://circleci.com/gh/uktrade/icms-hmrc)

# Introduction
This project sends licence updates to HMRC and updates ICMS with the response from HMRC for each licence.

It was originally called [lite-hmrc](https://github.com/uktrade/lite-hmrc) and was a shared repo that ICMS and LITE used to send updates to HMRC via CHIEF.

ICMS-HMRC has since removed all the lite code to simplify the maintenance burden for ICMS.

Tasks are managed using this project: [Celery](https://github.com/celery/celery)

The entry point for configuring the tasks is defined here: `icms-hmrc/conf/celery.py`


# Build and Run (in docker)
An `.env` file is expected at the root of project.

Copy the template file: `cp docker.env .env`

Copy the template local_settings.sample if required: `cp local_settings.sample local_settings.py`

if using local_settings.py remember to add this to your .env `DJANGO_SETTINGS_MODULE=local_settings`

To run in docker do the following
- Set up an `.env` file `cp docker.env .env`
- Start the containers: `make run-icms`
- Initial setup (run once):
  - Run migrations: `make migrate`
  - Create super user: `make createsuperuser`


**To check setup is working correctly navigate to the following url:** `http://localhost:8000/healthcheck/`

# Testing
Tests are located in `mail/tests` and `conf/tests`.

To run tests: `make test`

The tests require a live postgres server. They will create a database called
`test_postgres` as part of the test run.

# Linting

[Black](https://black.readthedocs.io/en/stable/) and isort are used in this project to enforce a consistent code style.

Apply formatting: `make format-all`

The tool `flake8` is used. To run it `make check-flake8`

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
