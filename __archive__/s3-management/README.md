# Minio-client (`mc`) S3 management — archived

Two CLI commands and their helper, moved out of
`py-modules/cli/macrostrat/cli/subsystems/storage.py` and **not wired up**:

| Was | Did |
| --- | --- |
| `macrostrat storage mc [args…]` | Ran arbitrary `mc` in a `minio/mc` container |
| `macrostrat storage mirror <src> <dst>` | `mc mb` + `mc mirror` between two buckets |
| `_mc(command)` | Built an `mc alias set` preamble and ran the script in Docker |

This is a holding area pending a decision on the longer-term shape of S3
management, not a judgement that the functionality isn't wanted. Nothing here
is imported, so it cannot run and cannot drift into use by accident; `ruff`
already excludes `__archive*`.

## Why they were moved

**They were already broken.** `_s3_users()` is called in `_mc` but is defined
nowhere in the repository — no definition, no import, no star-import. So `_mc`
raises `NameError` on its first loop, before any credential is fetched. Both
commands have been dead for some time, which is the main evidence that they
aren't load-bearing.

**rclone covers the actual work now.** `macrostrat storage s3-bucket-migration`
(still live) does bucket-to-bucket copying with rclone, and the `radosgw-admin`
subcommands cover cluster administration. `mc` sat between the two without
being needed by either.

**The credential handling needs redesign, not repair.** `_mc` interpolated an
access key and secret key **for every S3 user** into a shell script and passed
it as a single `argv` element to `docker run … /bin/sh -c <script>`. Had it
run, those credentials would have been readable on three surfaces:

- `ps` / `/proc/<pid>/cmdline` on the host — world-readable by default, for as
  long as the container lives, and `mc mirror` on a large bucket lives a long
  time. This is the one that matters: reading it needs no privilege.
- `docker inspect`, which exposes the container's `Cmd` while it is alive.
- The daemon connection itself. `docker_base_url` is configurable, so a TCP
  `DOCKER_HOST` would send the credential-bearing `Cmd` across a network.

Note the preamble aliased *every* user rather than the one in use, so a single
`macrostrat storage mc ls` would have exposed the whole set. The author was
careful about output — every `mc alias set` ends `> /dev/null 2>&1` — just not
about `argv`.

## If these are revived

1. **Pass the script on stdin, not in `argv`.** `--entrypoint=/bin/sh` with
   `-s` makes `sh` read the script from stdin, which leaves `Cmd` as `["-s"]`
   and `ps` showing nothing. `-it` has to become `-i`, so `mc`'s progress
   output degrades without a TTY — that is the trade.
   *Not* `-e` / `--env-file` with `MC_HOST_<alias>`: that fixes the `ps`
   surface but leaves the credentials visible to `docker inspect`.
2. **Alias only the user the command needs**, rather than every user.
3. **Take credentials from the storage layer**, i.e.
   `settings.storage_endpoint(name).credentials()`, so a reference in a secret
   manager works and the values stay redacted in logs.
4. **Define `_s3_users`**, or drop the multi-user preamble entirely.

Alternatively, delete this directory: if `s3-bucket-migration` and
`radosgw-admin` cover everything in practice, that is the cheapest outcome and
closes the channel permanently.
