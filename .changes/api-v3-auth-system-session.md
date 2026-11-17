---
api-v3: minor
---

- `/security/login`, `/security/callback` and `/security/refresh` come from `macrostrat.auth_system` 1.2.0
- Sign-in checks a state nonce, and returns only to the API's own origin or one listed in `AUTH_RETURN_ORIGINS`
- A refresh token is no longer accepted as a session
- FastAPI 0.136 and Starlette 1
