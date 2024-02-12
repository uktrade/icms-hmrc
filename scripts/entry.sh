#!/bin/sh -e

echo "Running migrations"
python manage.py migrate --noinput

if [ -n "${COPILOT_ENVIRONMENT_NAME}" ]; then
    echo "Running in DBT Platform"
    opentelemetry-instrument gunicorn conf.wsgi --config gunicorn.conf.py
else
    echo "Running in Cloud Foundry"
    # In DBT platform this will be done at the build stage.
    python manage.py collectstatic --noinput --traceback

    gunicorn conf.wsgi --config gunicorn.conf.py
fi
