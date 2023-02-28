vcl 4.1;

backend default {
    .host = "tileserver";
    .port = "8000";
}

sub vcl_deliver {
    if (obj.hits > 0) { # Add debug header to see if it's a HIT/MISS and the number of hits, disable when not needed
        set resp.http.X-Cache = "hit";
    } else {
        set resp.http.X-Cache = "miss";
    }
}
