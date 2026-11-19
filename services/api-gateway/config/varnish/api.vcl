vcl 4.1;

# Route to Caddy server on the same backend
backend default {
    .host = "localhost";
    .port = "8080";
    # Don't require the connection to be up at the start
    .probe = {
        .url = "/health";
        .timeout = 1s;
        .interval = 5s;
        .window = 5;
        .threshold = 3;
    }
}


# Bypass Varnish if tile has a cache=bypass query parameter
sub vcl_recv {
    # If the request is for /v2, remove all cookies (it is always safe to cache these routes)
    if (req.url ~ "^/v2") {
        unset req.http.Cookie;
    }

    # To remove expired cookies, we may need to decode them using Caddy first and then route to the appropriate backend

    # The task runner's routes are admin-only and one of them is a Server-Sent
    # Events stream: never cache them, and stream the response as it arrives.
    if (req.url ~ "^/v3/tasks(/|$)") {
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
    # If the cache was bypassed, indicate that in the response header
    # If the response header is already set to bypass, keep it that way
    if (req.http.X-Cache == "bypass") {
        set resp.http.X-Cache = "bypass";
    } else if (obj.hits > 0) {
        # Add debug header to see if it's a HIT/MISS and the number of hits, disable when not needed
        set resp.http.X-Cache = "hit";
    } else {
        set resp.http.X-Cache = "miss";
    }
}
