"""HTTP server for serving the Niam-Bay frontend."""

import os
import threading
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler


class FrontendServer:
    """Serves static files from the frontend directory."""

    def __init__(self, port: int = 8080, frontend_dir: str = "frontend"):
        self.port = port
        self.frontend_dir = os.path.abspath(frontend_dir)
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self):
        """Launch the HTTP server in a daemon thread."""
        handler = partial(SimpleHTTPRequestHandler, directory=self.frontend_dir)
        self._server = HTTPServer(("", self.port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        """Shut down the HTTP server."""
        if self._server:
            self._server.shutdown()
            self._server = None
            self._thread = None
