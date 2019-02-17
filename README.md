# Home Assistant Extension Index

## more info coming soon

Add an .env file to project root for docker environment setup containing:

```
# uncritical
IPYTHONDIR=/app/.ipython
HISTFILE=/app/.bash_history
DJANGO_LOG_LEVEL=DEBUG
DATABASE_URL=postgres://app:app@haindex-db:5432/app
ELASTIC_HOST=haindex-search:9200
CELERY_BROKER_URL=amqp://haindex-rabbitmq
DEBUG=True

# critical
GITHUB_API_USER=<yourGithubApiUser>
GITHUB_API_TOKEN=<yourGithubApiToken>
GITHUB_WEBHOOK_SECRET=<webhookSecretUsedOnHookCreation>
GITHUB_WEBHOOK_ENABLED=False
PAGE_URL=<basePageUrlUsedAsWebhookTarget>
RECAPTCHA_PUBLIC_KEY=<yourRecaptchaPublicKey>
RECAPTCHA_PRIVATE_KEY=<yourRecaptchaPrivateKey>
```