#!/bin/bash

while ! nc -z ${DB_HOST:-postgres} ${DB_PORT:-5432}; do
  echo Waiting for Postgres
  sleep 3
done

echo Applying migrations
python manage.py migrate --noinput

if [ "$DJANGO_ENV" == "production" ] || [ "$DJANGO_ENV" == "staging" ]; then
  if [ ! -d "hamlet/static" ]; then
    if [ -f "commit_id.txt" ]; then cp commit_id.txt static/ ; fi
    echo Generating static files
    python manage.py collectstatic --clear --no-input
  fi
  echo Starting production server
  exec gunicorn hamlet.wsgi -b 0:8080 -w 4 -t 60 --access-logfile - --capture-output
else
  echo Starting development server
  exec python manage.py runserver 0:8080
fi
