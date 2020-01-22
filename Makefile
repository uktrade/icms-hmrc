test:
	pipenv run ./manage.py test -v 2 --exclude-tag=end-to-end

test-in:
	docker exec -it lite-hmrc-intg make test

run:
	pipenv run ./manage.py runserver

check-format:
	black --check ./mail

cov:
	docker exec -it lite-hmrc-intg pipenv run coverage run --source='.' manage.py test mail --exclude-tag=end-to-end

cov-report:
	docker exec -it lite-hmrc-intg pipenv run coverage report
