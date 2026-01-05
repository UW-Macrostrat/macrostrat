# Community-driven map ingestion

## Problem statement

Macrostrat's mapping infrastructure has been extremely successful in ingesting maps, with over 300 to date.
However, most of the easy pickings (e.g., continent-scale geologic maps, the state geologic map compilation of North America)
have been exhausted. Also, most initial ingestion occurred in the Macrostrat lab, and was dependent on high time investment
by a small number of researchers and lab assistants.

We've got very little coverage of quad-scale maps globally. Building this coverage will require a new model wherein researchers
with a strong focus in a local area can contribute relevant mapping. This requires a high degree of automation and
guidance by external researchers.

## Envisioned stages of the Macrostrat mapping system

- [x] Basic map ingestion system that works well within the Macrostrat lab
- [x] Community-driven map ingestion system that works for community researchers
- [ ] Map ingestion system that accepts new (non-published) mapping with a review process
- [ ] Allow edits to existing mapping by community members
  ... leading us to an OpenStreetMaps for geology!

## Parts of the system

- A template PostGIS schema that serves as a target for ingestion
- A user interface that allows the PostGIS database dump to be uploaded
- A web form that allows checks and matching to be performed