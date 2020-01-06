## Introduction
This project is meant for sending license updates to HMRC and receiving usage reporting. Information like license updates
and usage are exchanged as mail attachment between Lite and HMRC

#### Local Dev Environment

- To build and run a local Postfix [mail server](git@github.com:uktrade/mailserver.git)
- To initilize database
`pipenv run ./manage.py migrate`
- To create database superuser `pipenv run ./manage.py createsuperuser`

#### To start the app

`pipenv run ./manage.py runserver`

#### Test
