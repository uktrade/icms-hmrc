FROM --platform=linux/amd64 python:3.10.7

WORKDIR /app

RUN apt update --fix-missing  \
    && apt install libpq-dev gcc -y  \
    && apt install build-essential -y --no-install-recommends

RUN pip3 install pipenv

ADD Pipfile* /app/

RUN pipenv sync --dev

ADD . /app
