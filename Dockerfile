FROM python:3.7-slim

LABEL maintainer="contact@zooniverse.org"

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libpq-dev \
    netcat \
    postgresql-client \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install \
  pipenv

WORKDIR /usr/src/app

COPY Pipfile ./
COPY Pipfile.lock ./

# set a default DJANGO_ENV for the build scripts
ARG DJANGO_ENV=production
ENV DJANGO_ENV=$DJANGO_ENV

RUN if echo "development test" | grep -w "$DJANGO_ENV"; then \
  pipenv install --system --dev; \
  else pipenv install --system; fi

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["bash", "start_server.sh"]
