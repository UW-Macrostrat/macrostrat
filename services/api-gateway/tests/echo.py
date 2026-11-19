"""Stand-in upstream for the gateway tests: answers with the request it received."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

NAME = os.environ["NAME"]


class Echo(BaseHTTPRequestHandler):
    def reply(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        body = json.dumps(
            {
                "service": NAME,
                "method": self.command,
                "path": self.path,
                "headers": {k.lower(): v for k, v in self.headers.items()},
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if NAME == "postgrest":
            self.send_header("Content-Range", "0-9/100")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    do_GET = do_HEAD = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = reply

    def log_message(self, *args):
        pass


ThreadingHTTPServer(("", 8000), Echo).serve_forever()
