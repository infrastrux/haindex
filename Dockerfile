FROM python:3.5.6-stretch

ENV PYTHONUNBUFFERED 1
ENV LC_ALL=C.UTF-8

RUN apt-get -y update && apt-get -y install \
      build-essential \
      gcc \
      python3-venv \
      python3-dev \
      libffi-dev \
      libpq-dev  \
      libssl-dev \
      gettext \
    && \
    apt-get clean && \
    mkdir /app && \
    useradd -m app

WORKDIR /app

USER app

ADD requirements.txt /app/

ENV PATH /home/app/venv/bin:${PATH}

RUN pyvenv ~/venv && \
    pip install --upgrade pip && \
    pip install wheel && \
    pip install -r requirements.txt

ADD . /app/

ENV DJANGO_SETTINGS_MODULE haindex.settings
