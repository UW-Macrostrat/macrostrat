---
api-v3: minor
---

- Serves every former tileserver route at its root; the `tileserver` service is retired
- CORS lets any origin read anonymously; listed origins keep credentialed access
- `/cache/refresh/carto` expires tiles in process; the internal `/cache/refresh/{prefix}` is gone (`/cache/flush` takes a prefix)
- Responses are compressed
- `/cache/flush` without a prefix expires tiles only; tile bans match the gateway's `/v3` and `/legacy-tiles` URLs as well as bare ones
