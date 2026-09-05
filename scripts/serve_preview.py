from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


class PreviewHandler(SimpleHTTPRequestHandler):
    api_base: str

    def _is_api_request(self) -> bool:
        return self.path.startswith("/api/") or self.path.split("?", 1)[0] in {"/health", "/ready"}

    def _proxy(self) -> None:
        body = None
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length:
            body = self.rfile.read(content_length)
        request_headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in HOP_BY_HOP_HEADERS | {"host", "content-length"}
        }
        request = urllib.request.Request(
            f"{self.api_base}{self.path}",
            data=body,
            headers=request_headers,
            method=self.command,
        )
        try:
            response = urllib.request.urlopen(request, timeout=30)
        except urllib.error.HTTPError as error:
            response = error
        except (urllib.error.URLError, TimeoutError) as error:
            payload = json.dumps(
                {
                    "error": {
                        "code": "preview_proxy_backend_unavailable",
                        "message": str(error),
                        "request_id": "preview-proxy",
                        "retryable": True,
                        "mode": "MOCK",
                    }
                }
            ).encode("utf-8")
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        payload = response.read()
        self.send_response(response.status)
        for key, value in response.headers.items():
            if key.lower() not in HOP_BY_HOP_HEADERS | {"content-length"}:
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        if self._is_api_request():
            self._proxy()
            return
        super().do_GET()

    def do_POST(self) -> None:
        self._proxy()

    def do_PUT(self) -> None:
        self._proxy()

    def do_OPTIONS(self) -> None:
        if self._is_api_request():
            self._proxy()
            return
        self.send_response(204)
        self.end_headers()


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve Trade Vision frontend with a same-origin API proxy.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    directory = args.directory.resolve()
    if not directory.is_dir():
        raise SystemExit(f"Frontend directory does not exist: {directory}")

    def handler(*handler_args, **handler_kwargs):
        instance = PreviewHandler(*handler_args, directory=str(directory), **handler_kwargs)
        return instance

    PreviewHandler.api_base = args.api_base.rstrip("/")
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Trade Vision preview: http://{args.host}:{args.port}")
    print(f"API proxy: {PreviewHandler.api_base}")
    server.serve_forever()


if __name__ == "__main__":
    main()
