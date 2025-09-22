#!/bin/sh
set -e

if [ "$SERVICE" = "web" ]
then
    python manage.py migrate --noinput
    exec gunicorn book_cit_web.wsgi:application --bind 0.0.0.0:$PORT
elif [ "$SERVICE" = "worker" ]
then
    exec celery -A book_cit_web worker --loglevel=info
elif [ "$SERVICE" = "beat" ]
then
    exec celery -A book_cit_web beat --loglevel=info
fi
