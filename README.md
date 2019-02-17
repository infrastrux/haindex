# Home Assistant Extension Index

## About

This project aims to provide a comprehensive index of [Lovelace plugins](https://developers.home-assistant.io/docs/en/lovelace_custom_card.html) and [custom components](https://developers.home-assistant.io/docs/en/development_index.html) for the [Home Assistant](https://www.home-assistant.io/) environment.

The production environment can be found on TBD

## Indexed data

Most of the indexed data is directly crawled from GitHub. However, extension maintainers can add more structured information in the form of a package.yaml file at the root level of their extension repository.

An example package.yaml looks like:

```yaml
name: My awesome extension
description: A short introduction to whatever my awesome extension does
type: lovelace
keywords:
  - awesome
  - terrific
  - gigantic
author:
  name: John Doe
  email: john@doe.com
  homepage: https://john.doe.com
license: MIT
dependencies:
  - thomasloven/lovelace-card-tools
files:
  - awesome-gigantic-card.js
```

More details about the package.yaml format can be found on TBD

## Contribute

The maintainers like this project to be as open as Home Assistant itself and welcome everyone to provide ideas and contribute to extending the functionality of the index. 

### Services

This project makes use of the GitHub API and Google's recaptcha.

You will need to have access to both of them to be able to start developing.

### Setup development environment

#### Prerequisites

A [docker-compose](https://docs.docker.com/compose/) environment is provided with this repository to make it as easy as possible to get up und running.

Please make sure that you're running

- docker (at least 17.12.0+)
- docker-compose (at least 1.18.0)

To manage your host file, the project relies on [Leo Antunes' docker-etchost](https://github.com/costela/docker-etchosts).

#### Docker

Project secrets are kept in environment. Please create a `.env` file at the project root with the following content and replace the placeholder (`<>`) with your actual secret data:

```
#####################
# uncritical
#####################

IPYTHONDIR=/app/.ipython
HISTFILE=/app/.bash_history
DJANGO_LOG_LEVEL=DEBUG
DATABASE_URL=postgres://app:app@haindex-db:5432/app
ELASTIC_HOST=haindex-search:9200
CELERY_BROKER_URL=amqp://haindex-rabbitmq
DEBUG=True

#####################
# critical
#####################

# your username on github
GITHUB_API_USER=<yourGithubApiUser>
# a personal access token as generated on https://github.com/settings/tokens
GITHUB_API_TOKEN=<yourGithubApiToken>
# any secret string that will be used to create and verify github webhook requests
GITHUB_WEBHOOK_SECRET=<webhookSecretUsedOnHookCreation>
# define if webhook creation should be enabled, your webserver must be publically accessible to receive webhooks
GITHUB_WEBHOOK_ENABLED=False
# the base url of your page that will be used as the webhook target
PAGE_URL=<basePageUrlUsedAsWebhookTarget>
# you recaptcha public and private keys as generated on https://www.google.com/recaptcha/admin
RECAPTCHA_PUBLIC_KEY=<yourRecaptchaPublicKey>
RECAPTCHA_PRIVATE_KEY=<yourRecaptchaPrivateKey>
```

The default docker-compose setup contains containers for
- Django
- PostgreSQL
- elasticsearch
- RabbitMQ
- Celery workers

start them all by running:

```bash
docker-compose up -d
```

Then migrate the database, load the prepared example data and rebuild the search index:

```bash
docker-compose run --rm django migrate
docker-compose run --rm django loaddata haindex/fixtures/repositories.json
docker-compose run --rm django search_index --rebuild
```

You're now ready to access your local copy on [http://haindex.ix-dev.eu:8000/](http://haindex.ix-dev.eu:8000/)
