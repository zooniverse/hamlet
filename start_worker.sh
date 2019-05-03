#!/bin/bash

echo Removing logs
rm tmp/*.log

echo Starting Celery
exec celery -A hamlet worker -l info
