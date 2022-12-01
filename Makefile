test:
	pipenv run pytest # --disable-warnings

test-in:
	docker exec -it lite-hmrc-intg make test

migrate:
	docker exec -it lite-hmrc-intg pipenv run ./manage.py migrate

migrations:
	docker exec -it lite-hmrc-intg pipenv run ./manage.py makemigrations

createsuperuser:
	docker exec -it lite-hmrc-intg pipenv run ./manage.py createsuperuser

shell:
	docker exec -it lite-hmrc-intg pipenv run ./manage.py shell -i python

run:
	pipenv run ./manage.py runserver

check-format:
	black --check ./mail

check-prospector:
	docker exec -it lite-hmrc-intg pipenv run prospector -W pylint -W pep257

cov:
	docker exec -it lite-hmrc-intg pipenv run coverage run --source='.' manage.py test mail

cov-report:
	docker exec -it lite-hmrc-intg pipenv run coverage report

run-icms:
	docker-compose -f docker-compose.yml -f docker-compose-icms.yml up --build -d

process-tasks:
	docker exec -it lite-hmrc-intg pipenv run ./manage.py process_tasks --log-std

# e.g. make pipenv COMMAND="install --dev requests-mock"
pipenv:
	docker exec -it lite-hmrc-intg pipenv ${COMMAND}
