# Usage stats changelog

## [Unreleased]

## [1.0.0] - 2026-11-20

- The image carries its build in `MACROSTRAT_*` environment variables
- Tag clients that send over 20,000 tiles an hour as bots, counting IPv6 clients by /64
- Requests the tile render limit refused (429) are left out of tile counts and recorded per client and day in `tileserver_throttled_clients`, with report-mode `would-deny` marks
