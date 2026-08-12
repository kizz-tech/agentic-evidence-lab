from __future__ import annotations

import json
import os
import select
import socket
import socketserver
from datetime import UTC, datetime

LISTEN_PORT = int(os.environ.get("AEL_PROXY_PORT", "3128"))
ALLOWED_HOSTS = {
    host.strip().lower().rstrip(".")
    for host in os.environ.get(
        "AEL_ALLOWED_HOSTS",
        "api.openai.com,auth.openai.com,chatgpt.com",
    ).split(",")
    if host.strip()
}
MAX_HEADER_BYTES = 64 * 1024


def emit(event: str, **fields: object) -> None:
    print(
        json.dumps(
            {"at": datetime.now(UTC).isoformat(), "event": event, **fields},
            sort_keys=True,
        ),
        flush=True,
    )


class ConnectHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        self.connection.settimeout(20)
        request_line = self.rfile.readline(MAX_HEADER_BYTES + 1)
        if not request_line or len(request_line) > MAX_HEADER_BYTES:
            return
        try:
            method, target, _version = request_line.decode("ascii").strip().split(" ", 2)
        except (UnicodeDecodeError, ValueError):
            self._reject(400, "bad request")
            return

        consumed = len(request_line)
        while True:
            line = self.rfile.readline(MAX_HEADER_BYTES + 1)
            consumed += len(line)
            if consumed > MAX_HEADER_BYTES:
                self._reject(431, "headers too large")
                return
            if line in {b"\r\n", b"\n", b""}:
                break

        if method.upper() != "CONNECT" or ":" not in target:
            self._reject(405, "CONNECT required")
            return
        host, port_text = target.rsplit(":", 1)
        host = host.lower().rstrip(".")
        try:
            port = int(port_text)
        except ValueError:
            self._reject(400, "bad port")
            return
        if host not in ALLOWED_HOSTS or port != 443:
            emit("blocked", host=host, port=port)
            self._reject(403, "egress denied")
            return

        try:
            upstream = socket.create_connection((host, port), timeout=20)
        except OSError as exc:
            emit("upstream_error", host=host, port=port, error=type(exc).__name__)
            self._reject(502, "upstream unavailable")
            return

        emit("allowed", host=host, port=port)
        self.wfile.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        self.wfile.flush()
        upstream.setblocking(False)
        self.connection.setblocking(False)
        sockets = [self.connection, upstream]
        try:
            while sockets:
                readable, _, exceptional = select.select(sockets, [], sockets, 60)
                if exceptional or not readable:
                    break
                for source in readable:
                    target_socket = upstream if source is self.connection else self.connection
                    try:
                        payload = source.recv(64 * 1024)
                    except OSError:
                        payload = b""
                    if not payload:
                        return
                    target_socket.sendall(payload)
        finally:
            upstream.close()

    def _reject(self, status: int, message: str) -> None:
        body = (message + "\n").encode("utf-8")
        self.wfile.write(
            f"HTTP/1.1 {status} {message}\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode(
                "ascii"
            )
            + body
        )
        self.wfile.flush()


class ProxyServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    emit("started", port=LISTEN_PORT, allowed_hosts=sorted(ALLOWED_HOSTS))
    try:
        with ProxyServer(("0.0.0.0", LISTEN_PORT), ConnectHandler) as server:
            server.serve_forever()
    except KeyboardInterrupt:
        emit("stopped")
    except Exception as exc:
        emit("fatal", error=type(exc).__name__)
        raise
