# Map Ingestion

## Objects schema (table)

The purpose of this schema is to track objects that Macrostrat is aware of.

> Note: Informally, we may refer to these objects as "files".

### Main columns

- id: Primary key. An integer with no other meaning attached to it.

- scheme: A string indicating the kind of object store. Examples include:

  - `s3`: A service that uses the Amazon S3 protocol. Note that Amazon S3
    is not the only service that implements this protocol.

  - `http`: A service that uses the HTTP protocol. For example, any web site
    that is accessible using a standard web browser.

- host: A string containing the object store's hostname.

- bucket: A string containing the bucket's name within the object store.
  Note that not all object stores have a well-defined notion of "bucket".

- key: A string containing the object's name within the object store and,
  if applicable, bucket.

- source: JSON object describing the provenance of the object indicated by
  the columns above. We use JSON here because it's machine-readable but does
  not otherwise require that we settle on a sub-schema.

We need several constraints on these columns to ensure that records are
(minimally) well-formed and that there is at most one record per object:

- scheme: Not null.

- host: Not null.

- key: Not null.

- (scheme, host, bucket, key): Unique.

To make it feasible to determine whether an object exists in the schema:
we need one index:

- A multiple-column index on (scheme, host, bucket, key).

### Other columns

The following columns record metadata about the object.

- mime\_type: String containing the object's media type (a.k.a. MIME type).

- sha256\_hash: String containing the object's SHA-256 hash in hexadecimal.

The following columns record metadata about the record itself. Some SQL
interfaces might maintain this information automatically.

- created\_at: UNIX timestamp for when this record was originally created.

- modified\_at: UNIX timestamp for when this record was last modified.

- deleted\_at: UNIX timestamp for when this record was marked as "deleted."

### Design and implementation considerations

This schema does not commit us to storing objects in any one particular
system or place. However, to start, we expect that everything will be stored
in a single S3-compatible object store, using one set of credentials that
has read/write access to the relevant bucket(s).

If necessary, we may add a column to the schema for storing foreign keys
into a "credentials" schema.

For objects that can be retrieved using a simple, unauthenticated HTTP GET
request, it may be helpful to have a computed or virtual column containing
the requisite URL.

## Workflow for ingesting one file

Nothing fancy here:

1. Put the file into the object store.

2. Add a row to the above schema.

The details depend on who/what is attempting to get a file into Macrostrat.
