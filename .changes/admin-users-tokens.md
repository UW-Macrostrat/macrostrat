---
api-v3: minor
---

- `PATCH /security/users/{id}` also changes display name and email; an admin may edit their own record but not their own role
- `DELETE /security/users/{id}` deletes a user; tokens delegated to them are expired and kept
- `PATCH /security/tokens/{id}` replaces a token's scopes
- `GET /security/tokens` names the delegated user (`user_name`)
