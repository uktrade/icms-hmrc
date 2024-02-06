
#
# Aliases
#
run = docker-compose run --rm
pipenv = $(run) -e DJANGO_SETTINGS_MODULE=conf.settings web-api pipenv run

#
# Commands
#
run-icms:
	docker-compose -f docker-compose.yml up --build -d

stop-icms:
	docker-compose stop

down: ## Stops and downs containers
	docker-compose down --remove-orphans

manage: ## execute manage.py
	$(pipenv) ./manage.py ${args}

test:
	$(run) -e DJANGO_SETTINGS_MODULE=conf.settings_test web-api pipenv run pytest ${args} # --disable-warnings

migrate:
	$(pipenv) ./manage.py migrate

migrations:
	$(pipenv) ./manage.py makemigrations

squashmigrations:
	$(pipenv) ./manage.py squashmigrations ${args}

diffsettings:
	$(pipenv) ./manage.py diffsettings

createsuperuser:
	$(pipenv) ./manage.py createsuperuser

shell:
	$(pipenv) ./manage.py shell -i python


fake_dbt_built: ## Fake build command (builds static files without connection details to backing services)
	$(run) -e DJANGO_SETTINGS_MODULE=conf.settings -e BUILD_STEP=True -e COPILOT_ENVIRONMENT_NAME=DUMMY web-api pipenv run ./manage.py collectstatic --noinput --traceback

#
# linting / formatting commands
#
format-all:
	$(pipenv) isort . && \
	$(pipenv) black .

check-flake8:
	$(pipenv) flake8 --ignore=E501,W503

cov:
	$(pipenv) coverage run --source='.' manage.py test mail

cov-report:
	$(pipenv) coverage report
