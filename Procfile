# See gunicorn.conf.py for more configuration.
web: python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn conf.wsgi:application
celery_beat: celery -A conf beat -l INFO
celery_worker: celery -A conf worker -l INFO
