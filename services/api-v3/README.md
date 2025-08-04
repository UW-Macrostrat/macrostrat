# Macrostrat API V3

## Overview

This is a Fastapi application interfacing with a postgres database. It is designed to be deployed behind
Nginx on a kubernetes cluster.

## Development

.env

```shell
uri=postgresql://...

REDIRECT_URI_ENV=http://localhost:8000/security/callback

OAUTH_AUTHORIZATION_URL=https://cilogon.org/authorize
OAUTH_TOKEN_URL=https://cilogon.org/oauth2/token
OAUTH_USERINFO_URL=https://cilogon.org/oauth2/userinfo

OAUTH_CLIENT_ID=
OAUTH_CLIENT_SECRET=

SECRET_KEY=<AnyRandomHash>
JWT_ENCRYPTION_ALGORITHM=HS256

access_key=<S3_ACCESS_KEY>
secret_key=<S3_SECRET_KEY>

ENVIRONMENT=development # This turns off authentication when running locally
```

## Creating a token

Assuming you are running locally on localhost:8000

1. Login in to the api via [http://localhost:8000/security/login](http://localhost:8000/security/login)

2. Grab a security token via
   POST [http://localhost:8000/docs#/security/create_group_token_security_token_post](http://localhost:8000/docs#/security/create_group_token_security_token_post)

   Set the group_id to 1 ( admin group ) and the expiration to the future ( 1832530128 = 2028-01-26 )
