vcl 4.1;

backend backend-core {
    .host = "tileserver_core";
    .port = "8000";
}


backend backend-legacy {
    .host = "tileserver_legacy";
    .port = "8000";
    # Don't require the connection to be up at the start
}


# Private address space: the docker-compose network locally, the pod network in
# the cluster. Used only to gate BAN — see vcl_recv.
acl internal {
    "localhost";
    "10.0.0.0"/8;
    "172.16.0.0"/12;
    "192.168.0.0"/16;
}


# Bypass Varnish if tile has a cache=bypass query parameter
sub vcl_recv {
    # Cache invalidation via BAN, from inside the network only.
    #
    # The comment this replaces asserted the docker network was the only way in,
    # but nothing enforced it: a BAN sent to the public tiles host reached this
    # handler and flushed the cache. Two conditions gate it now.
    #
    # The client must be on a private address — and, because the edge proxy is
    # itself on one, that alone cannot tell an internal caller from a proxied
    # external one. The second condition does: Varnish stamps its own view of
    # the client into X-Forwarded-For on every request, so a direct internal
    # call arrives with exactly one entry, while one relayed by the edge proxy
    # (Caddy locally, Traefik in the cluster) carries the proxy's entry plus
    # Varnish's — two entries, hence a comma. A forged header does not help an
    # attacker: the proxy appends to whatever it is given, so the comma appears
    # either way.
    if (req.method == "BAN") {
        if (req.http.X-Forwarded-For ~ "," || client.ip !~ internal) {
            return(synth(403, "Cache invalidation is internal-only"));
        }
        if (!req.http.X-Ban-Expression) {
            return(synth(400, "Missing X-Ban-Expression header"));
        }
        ban(req.http.X-Ban-Expression);
        return(synth(200, "Banned"));
    }

    # The tileserver's cache-management routes expire both cache layers, so they
    # are reached through the admin-gated /api/v3/cache proxy and are not served
    # to the public. The footprints tile layer is a read that the cache UI draws,
    # so it stays open.
    if (req.url ~ "^/cache/" && req.url !~ "^/cache/footprints/") {
        return(synth(403, "Cache management is internal-only"));
    }

    # Set the backend hints to route to the correct upstream
    # For now the index.html route is served from the legacy tileserver
    if (req.url ~ "^/rasters/") {
        # Raster mosaics are served as .png by the core tileserver, so they have
        # to be claimed before the extension-based rule below sends every .png
        # to the legacy one.
        set req.backend_hint = backend-core;
    } else if (req.url ~ "^/$" || req.url ~ "^/preview$") {
        set req.backend_hint = backend-legacy;
    } else if (req.url ~ ".*\.(png|mvt)$") {
        # Png and mvt tiles are served from the legacy tileserver
        set req.backend_hint = backend-legacy;
    } else {
        # Everything else is served from the core tileserver
        set req.backend_hint = backend-core;
        # TODO: could add a v3 prefix here if needed
    }

    # Bypass the cache for zoom levels greater than 14
    if (req.url ~ ".*\/([0-9][56789]|[0-9]{3,})\/[0-9]+\/[0-9]+(\.png|\.mvt)?") {
        set req.http.X-Cache = "bypass";
        return (pass);
    }


    if (req.url ~ ".*cache=bypass.*") {
        set req.http.X-Cache = "bypass";
        return (pass);
    }

    # If has no-cache header, bypass Varnish
    # This might be redundant, I'm not quite sure what the default behavior is
    if (req.http.Cache-Control ~ "no-cache") {
        set req.http.X-Cache = "bypass";
        return (pass);
    }

    # Guarded map tiles (`/map/<slug>/{z}/{x}/{y}`) are cached despite their
    # `Authorization` header, which the built-in rules would otherwise pass
    # straight to the backend. The token is cost control: the tileserver spends
    # a render only for a known caller, and a cached tile costs no render. So a
    # hit is served to anyone, and a miss goes to the tileserver, which checks
    # the token before it touches the database. The header is not part of the
    # cache key, so every caller shares one copy of each tile.
    #
    # Interim, by decision (2026-09-28): the intent is to verify the token here
    # instead -- it is HS256, an HMAC-SHA256 over the header and payload plus an
    # `exp` check -- once the image carries an HMAC VMOD, so that tokens can
    # gate access and not only cost. Until then, nothing that must stay private
    # may be served under `/map/`.
    if ((req.method == "GET" || req.method == "HEAD") &&
        req.url ~ "^/map/[^/]+/[0-9]+/[0-9]+/[0-9]+(\?.*)?$") {
        return (hash);
    }
}

sub vcl_deliver {
    # Internal bookkeeping (see vcl_backend_response), not for clients.
    unset resp.http.X-Ban-Url;

    # The tileserver answers any origin (`*`), but adds the header only when a
    # request carries `Origin`, and a cached object keeps the headers of the
    # request that filled it. Filled by a caller without one -- a script, a
    # proxy -- a tile would then reach every browser without the header and be
    # refused as a CORS failure. Restated here, on delivery, so no cached
    # object depends on who asked for it first.
    if (req.http.Origin && !resp.http.Access-Control-Allow-Origin) {
        set resp.http.Access-Control-Allow-Origin = "*";
    }

    if (obj.hits > 0) {
        # Add debug header to see if it's a HIT/MISS and the number of hits, disable when not needed
        set resp.http.X-Cache = "hit";
    } else {
        set resp.http.X-Cache = "miss";
    }
}

sub vcl_backend_response {
    # Record the cached URL on the object so invalidations can be written over
    # obj.*. A ban over req.url cannot be applied by the background ban lurker,
    # so it stays on the ban list and is re-tested against every request for the
    # life of the process; one over obj.* is retired once it has been applied.
    set beresp.http.X-Ban-Url = bereq.url;

    # A guarded tile is looked up whatever its token (vcl_recv), so only a tile
    # may be stored: a 401 for a caller without one, or any other error, cached
    # under the tile's URL would be served to callers who have one. Marked
    # hit-for-miss, so each such request goes to the backend on its own.
    if (bereq.url ~ "^/map/[^/]+/[0-9]+/[0-9]+/[0-9]+" && beresp.status != 200) {
        set beresp.uncacheable = true;
        set beresp.ttl = 30s;
        return (deliver);
    }

    # Set a long TTL for tiles
    if (bereq.url ~ ".*\.(png|mvt)$") {
        set beresp.ttl = 1d;
        # Allow stale content while revalidating
        set beresp.grace = 5m;
    } else if (beresp.http.Content-Type ~ "application/x-protobuf") {
        # Vector tiles should have the same TTL
        set beresp.ttl = 1d;
        set beresp.grace = 5m;
    } else {
        # Shorter TTL for other content
        set beresp.ttl = 5m;
    }
}
