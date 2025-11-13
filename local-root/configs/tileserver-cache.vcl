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


# Bypass Varnish if tile has a cache=bypass query parameter
sub vcl_recv {
    # Set the backend hints to route to the correct upstream
    # For now the index.html route is served from the legacy tileserver
    if (req.url ~ "^/$" || req.url ~ "^/preview$") {
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
}

sub vcl_deliver {
    if (obj.hits > 0) {
        # Add debug header to see if it's a HIT/MISS and the number of hits, disable when not needed
        set resp.http.X-Cache = "hit";
    } else {
        set resp.http.X-Cache = "miss";
    }
}
