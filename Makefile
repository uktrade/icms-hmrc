
#
# Aliases
#
run = docker-compose run --rm
pipenv = $(run) -e DJANGO_SETTINGS_MODULE=conf.settings lite-hmrc-intg pipenv run

#
# Commands
#
run-icms:
	docker-compose -f docker-compose.yml -f docker-compose-icms.yml up --build -d

stop-icms:
	docker-compose stop

test:
	$(run) -e DJANGO_SETTINGS_MODULE=conf.settings_test lite-hmrc-intg pipenv run pytest ${args} # --disable-warnings

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

check-format:
	$(pipenv) black .

check-prospector:
	$(pipenv) prospector -W pylint -W pep257

cov:
	$(pipenv) coverage run --source='.' manage.py test mail

cov-report:
	$(pipenv) coverage report

process-tasks:
	$(pipenv) ./manage.py process_tasks --log-std
