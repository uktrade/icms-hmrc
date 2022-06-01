test:
	pipenv run ./manage.py test -v 2

test-in:
	docker exec -it lite-hmrc-intg make test

migrate:
	docker exec -it lite-hmrc-intg pipenv run ./manage.py migrate

createsuperuser:
	docker exec -it lite-hmrc-intg pipenv run ./manage.py createsuperuser

run:
	pipenv run ./manage.py runserver

check-format:
	black --check ./mail

cov:
	docker exec -it lite-hmrc-intg pipenv run coverage run --source='.' manage.py test mail

cov-report:
	docker exec -it lite-hmrc-intg pipenv run coverage report
