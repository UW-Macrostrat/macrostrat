# Map Ingestion

## Files schema (table)

The purpose of this schema is to track files that Macrostrat is aware of.

Assumptions:

- We store everything in one or more S3 object stores.

- Credentials for the S3 object stores are tracked separately.

To start, we will use one S3 object store with one set of credentials that
has read/write access to the relevant bucket(s). The schema is designed so
that we can point to S3 object stores hosted by others.

Columns:

- id: Primary key. An integer with no other meaning attached to it.

- s3\_host: A string containing the S3 object store's hostname.

- s3\_bucket: A string containing the S3 bucket's name within the object store.

- s3\_object: A string containing the S3 object's name within the bucket.

- source: JSON object describing where this file originated. We use JSON
  here because it's machine-readable but does not otherwise require that we
  settle on a sub-schema. We want to track the provenance of files but not
  necessarily make any decisions based on that information.

Constraints to ensure one record per S3 object:

- s3\_host: Not null.

- s3\_bucket: Not null.

- s3\_object: Not null.

- (s3\_host, s3\_bucket, s3\_object): Unique

Potential indexes:

- A multiple-column index on (s3\_host, s3\_bucket, s3\_object). Makes it
  feasible to determine whether an object in S3 has been recorded.

Additional columns can be added as needed, e.g., to record metadata about
objects that might be expensive to compute.

## Workflow for ingesting one file

Nothing fancy here:

1. Put the file into the S3 object store.

2. Add a row to the above schema.

The details depend on who/what is attempting to get a file into Macrostrat.
