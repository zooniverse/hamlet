FROM python:3.7-slim

LABEL maintainer="contact@zooniverse.org"

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libpq-dev \
    netcat-openbsd \
    postgresql-client \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install poetry

WORKDIR /usr/src/app

COPY pyproject.toml ./
COPY poetry.toml ./
COPY poetry.lock ./

# set a default DJANGO_ENV for the build scripts
ARG DJANGO_ENV=production
ENV DJANGO_ENV=$DJANGO_ENV

RUN if echo "development test" | grep -w "$DJANGO_ENV"; then \
  poetry install; \
  else poetry install --no-dev; fi

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["bash", "start_server.sh"]
