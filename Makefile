alltest:
	pipenv run ./manage.py test -v 2

run:
	pipenv run ./manage.py runserver

check-format:
	black --check ./mail

cov:
	pipenv run coverage run --source='.' manage.py test mail

cov-report:
	pipenv run coverage report
