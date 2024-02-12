# See gunicorn.conf.py for more configuration.
web: scripts/entry.sh
celery_beat: celery -A conf beat -l INFO
celery_worker: celery -A conf worker -l INFO
