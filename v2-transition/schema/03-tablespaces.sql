-- https://www.postgresql.org/docs/current/ddl-partitioning.html

CREATE TYPE map_scale AS ENUM ('tiny', 'small', 'medium', 'large');

/* Apply partitions to existing maps tables */
