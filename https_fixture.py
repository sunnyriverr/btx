"""Loopback TLS relay for the disposable ModelNet MinIO recovery test."""
import http.client
import http.server
import ssl
import threading
import time
from urllib.parse import urlsplit


class MinioRelay:
    def __init__(self, origin, cert, key):
        upstream = urlsplit(origin)
        assert upstream.scheme == "http" and upstream.hostname == "127.0.0.1"
        self.events = []
        self.delayed_path = None
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def forward(self):
                match = self.command == "GET" and self.path == owner.delayed_path
                received = time.monotonic()
                if match:
                    owner.events.append((self.command, self.path, "delay", received))
                    time.sleep(8)
                    return
                request = http.client.HTTPConnection(upstream.hostname, upstream.port, timeout=15)
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                    body = self.rfile.read(size) if size else None
                    request.request(self.command, self.path, body, dict(self.headers))
                    response = request.getresponse()
                    owner.events.append((self.command, self.path, response.status, received))
                    self.send_response_only(response.status)
                    for name, value in response.getheaders():
                        if name.lower() not in {"connection", "transfer-encoding"}:
                            self.send_header(name, value)
                    self.send_header("Connection", "close")
                    self.end_headers()
                    if self.command != "HEAD":
                        while chunk := response.read(64 << 10):
                            self.wfile.write(chunk)
                finally:
                    request.close()

            do_GET = do_PUT = do_HEAD = do_DELETE = forward

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        self.endpoint = f"https://localhost:{self.server.server_port}"
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.worker.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join()
