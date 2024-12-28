# API Tests

## Running the tests

To run the tests, you need to have the following environment variables set or available in a `.env` file.

The ADMIN_TOKEN is an api token used to authenticate as an admin user.

```bash
uri=

REDIRECT_URI=http://localhost:8000/security/callback

OAUTH_AUTHORIZATION_URL=https://cilogon.org/authorize
OAUTH_TOKEN_URL=https://cilogon.org/oauth2/token
OAUTH_USERINFO_URL=https://cilogon.org/oauth2/userinfo

OAUTH_CLIENT_ID=
OAUTH_CLIENT_SECRET=

SECRET_KEY=
JWT_ENCRYPTION_ALGORITHM=HS256

ADMIN_TOKEN=
```
