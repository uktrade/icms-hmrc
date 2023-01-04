# See gunicorn.conf.py for more configuration.
web: python manage.py migrate && gunicorn conf.wsgi:application
celery_beat: celery -A conf beat -l INFO
celery_worker: celery -A conf worker -l INFO
dbt_worker: python manage.py process_tasks --log-std
