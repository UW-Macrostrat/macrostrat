# API gateway for Macrostrat's API and tile hosts: Caddy routes, Varnish caches.
# One image, so the Caddyfiles and VCLs always match; it runs as separate Caddy
# and Varnish containers, each with its own limits, restarts and logs.
FROM caddy:2.9.1-alpine AS caddy

FROM varnish:7.7.3

USER root

# Caddy runs as the image's unprivileged user but listens on :80
RUN apt-get update \
 && apt-get install -y --no-install-recommends libcap2-bin \
 && rm -rf /var/lib/apt/lists/*

COPY --from=caddy /usr/bin/caddy /usr/bin/caddy
RUN setcap cap_net_bind_service=+ep /usr/bin/caddy \
 && mkdir -p /data /config /tmp/gateway /usr/share/gateway \
 && chown varnish /data /config /tmp/gateway

ENV XDG_CONFIG_HOME=/config \
    XDG_DATA_HOME=/data

COPY bin/gateway /usr/local/bin/gateway
COPY config /etc/gateway

ARG MACROSTRAT_VERSION MACROSTRAT_RELEASE MACROSTRAT_COMMIT MACROSTRAT_BUILD_DATE MACROSTRAT_REPOSITORY
ENV MACROSTRAT_VERSION=$MACROSTRAT_VERSION \
    MACROSTRAT_RELEASE=$MACROSTRAT_RELEASE \
    MACROSTRAT_COMMIT=$MACROSTRAT_COMMIT \
    MACROSTRAT_BUILD_DATE=$MACROSTRAT_BUILD_DATE \
    MACROSTRAT_REPOSITORY=$MACROSTRAT_REPOSITORY
RUN gateway write-version /usr/share/gateway/version.json

USER varnish

ENTRYPOINT ["/usr/local/bin/gateway"]
CMD ["caddy"]
