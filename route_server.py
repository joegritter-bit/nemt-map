import http.server
import socketserver
import os

PORT = 8765
DIRECTORY = os.path.join(os.path.expanduser('~'), 'nemt-scraper')


class RouteHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def log_message(self, format, *args):
        pass  # Suppress access logs

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()


def start_server():
    with socketserver.TCPServer(("", PORT), RouteHandler) as httpd:
        httpd.allow_reuse_address = True
        print(f"   🌐 Route Builder server running at "
              f"http://localhost:{PORT}/route_builder.html")
        httpd.serve_forever()


if __name__ == "__main__":
    start_server()
