#!/bin/bash
pipenv run ./manage.py migrate
pipenv run ./manage.py emit_test_background_task
pipenv run ./manage.py process_tasks --queue test_queue
