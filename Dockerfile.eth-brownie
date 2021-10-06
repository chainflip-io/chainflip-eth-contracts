FROM python:3.9.7-bullseye

USER root

RUN apt-get update -y \
    && apt-get install curl

RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | python -

RUN curl -fsSL https://deb.nodesource.com/setup_14.x | sh - \
    && apt-get install -y nodejs

RUN npm install --global ganache-cli \
    && ganache-cli --version

ENV PATH="/root/.local/bin:${PATH}"
