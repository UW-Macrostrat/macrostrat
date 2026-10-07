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

## Accounts, roles and sessions

Sign-in is ORCID (through CILogon). The first sign-in creates a row in
`macrostrat_auth."user"` in the `user` role. The session is a JWT in the
`access_token` cookie, whose `role` claim is the **Postgres role** PostgREST
assumes for every request; a `refresh_token` cookie re-mints it for a week.
The web app verifies the same JWT with the shared `SECRET_KEY`.

The tiers nest, each inheriting the grants of the one below:

| Application role (`macrostrat_auth.role`) | Postgres role     | Who                                                              |
| ----------------------------------------- | ----------------- | ---------------------------------------------------------------- |
| *(not signed in)*                         | `web_anon`        | Everyone. Most of Macrostrat is readable anonymously.           |
| `user`                                    | `web_user`        | Anyone who signs in. Confers nothing substantial over `web_anon`. |
| `authorized`                              | `web_authorized`  | Designated by an admin. May view anything, including work in progress; edits nothing of record. |
| `admin`                                   | `web_admin`       | Makes real edits and administers users and tokens.               |

Grant read access for signed-in collaborators to `web_authorized`, never to
`web_user`, since anyone can hold the latter.

The routes under `/security`:

| Route                           | Who    | What                                                                                   |
| ------------------------------- | ------ | -------------------------------------------------------------------------------------- |
| `GET /login`, `GET /callback`   | anyone | The OAuth flow. `login?return_url=` comes back to that page.                           |
| `POST /refresh`, `POST /logout` | anyone | Re-mint or clear the session cookies.                                                  |
| `GET /me`                       | signed in | The stored record plus the session's `role`, `actual_role`, `app_role`, `degraded`. |
| `POST /role`                    | signed in | Re-mint the session in a *lower* Postgres role, or `{"role": null}` to restore. Lets an admin see the site as a user does. The degraded token carries `actual_role`. |
| `GET /users`, `PATCH /users/{id}`, `GET /roles` | admin | List and search accounts, move one between roles (never your own). |
| `GET /tokens`, `POST /tokens`, `POST /tokens/{id}/revoke` | admin | Delegated API tokens: list (never the values), mint, revoke. |
| `GET /history`                  | admin  | Recent changes to users and tokens from the audit trail.                               |

All of this has a UI at **`/dashboard`** (your own account) and
**`/dashboard/admin`** (users, tokens, role switching, system introspection) on
the website; the persona control in page headers turns yellow while a session
is degraded.

Every cookie-issuing route derives its cookie attributes from
`auth_cookie_params()`, so a session re-issued by a refresh or a role switch
lands where the login put it. Locally the API runs at a `.local` subdomain and
the cookie is scoped to the parent domain with `SameSite=None`.

### Audit trail

`macrostrat_auth."user"` and `macrostrat_auth.token` are on the audit roster
(`schema/_definitions/audit/20-enable.sql`). Role changes and token minting or
revocation made through this API are attributed to the acting admin as
`orcid:<ORCID iD>`, the same spelling the trigger uses for writes that arrive
through PostgREST, via `audit.set_context` in the writing transaction. Read it
with `GET /security/history`, or in the database:

```sql
select * from audit.changes where schema_name = 'macrostrat_auth' order by id desc;
```

## Delegated API tokens

A delegated token lets a service or a third party reach a guarded endpoint
without a browser session. It is a JWT signed with `SECRET_KEY`, but authority
comes from its stored row (`macrostrat_auth.token`), which carries the scopes;
only the token's sha256 digest is stored, so a lost token is reissued rather
than recovered, and revoking one expires the row.

Mint one from the website (`/dashboard/admin` → API tokens → New token), from
the CLI (`macrostrat auth create-token --label '…' --scope rasters:emit-minerals
--days 365`), or with `POST /security/tokens` as an admin:

```json
{ "label": "Colorado School of Mines - EMIT", "scopes": ["rasters:emit-minerals"], "expiration": 1832530128 }
```

`expiration` is a Unix timestamp. Give `label` for a third party or `user_id`
to delegate a Macrostrat user's authority; at least one is required. Scopes
are `namespace:resource`. List with `GET /security/tokens` or `macrostrat auth
list-tokens`; revoke with `POST /security/tokens/{id}/revoke` or `macrostrat
auth revoke-token <id>`.
