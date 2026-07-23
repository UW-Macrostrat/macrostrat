FROM caddy:2.11.4-builder AS builder

RUN xcaddy build --with github.com/protomaps/go-pmtiles/caddy

FROM caddy:2.11.4
