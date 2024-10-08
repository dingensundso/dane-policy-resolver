#!/usr/bin/env python3
import logging
import signal
import socket
import socketserver
import threading
from types import FrameType

logger = logging.getLogger(__name__)


class SocketServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = False
    block_on_close = True
    _is_interrupted = False

    def server_activate(self) -> None:
        logger.info(
            "Server started on %s:%s",
            *self.server_address,
        )
        for sig in (
            signal.SIGHUP,
            signal.SIGINT,
            signal.SIGTERM,
            signal.SIGQUIT,
        ):
            signal.signal(sig, self.signal_handler)
        super().server_activate()

    def get_request(self) -> tuple[socket.socket, str]:
        conn, addr = super().get_request()
        logger.debug("Starting connection from %s:%s", *addr)
        return conn, addr

    def shutdown(self) -> None:
        self._is_interrupted = True
        logger.info("Server is shutting down...")
        super().shutdown()

    def signal_handler(self, signum: int, _: FrameType | None) -> None:
        signame = signal.Signals(signum).name
        logger.debug("%s received." % signame)
        self.shutdown()


class RequestHandler(socketserver.BaseRequestHandler):
    server: SocketServer

    def setup(self) -> None:
        self.request.settimeout(1)

    def handle(self) -> None:
        while True:
            if self.server._is_interrupted:
                break

            try:
                data = self.request.recv(1024)

                if not data:
                    break

                logger.debug(
                    f"recv from %s:%s: {data!r}",
                    *self.client_address,
                )
                self.handle_data(data)
            except socket.timeout:
                continue

    def finish(self) -> None:
        logger.debug("Closing connection from %s:%s", *self.client_address)

    def handle_data(self, data: bytes) -> None:
        self.request.sendall(data)


def run_server(
    host: str = "localhost",
    port: int = 8460,
    handler: type[socketserver.BaseRequestHandler] = RequestHandler,
) -> None:
    with SocketServer((host, port), handler) as server:
        t = threading.Thread(target=server.serve_forever)
        t.start()
        try:
            import sd_notify  # type: ignore

            notify = sd_notify.Notifier()
            if notify.enabled():
                logger.debug("Notifying systemd that we are ready.")
                notify.ready()
            else:
                logger.debug("Not running as systemd unit.")
        except ModuleNotFoundError:
            logger.debug("sd-notify is not installed. Unable to notify systemd.")
        t.join()
