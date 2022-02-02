FROM python:3.7-slim
ENV DOCKERIZE_VERSION v0.6.1
RUN apt-get update --fix-missing
RUN apt-get install libpq-dev gcc wget -y
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz
WORKDIR /app
RUN pip3 install pipenv
ADD Pipfile* /app/
RUN pipenv sync --dev
ADD . /app
WORKDIR /app
