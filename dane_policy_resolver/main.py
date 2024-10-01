import logging
from enum import Enum
from typing import Annotated, Optional

import typer

from .resolver import Handler, is_dnssec_supported, resolver
from .server import run_server

logger = logging.getLogger(__name__)


class LogLevels(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def main(
    host: str = "localhost",
    port: int = 8460,
    nameservers: Annotated[
        Optional[str],
        typer.Option(
            help="comma-seperated list of nameservers. default uses /etc/resolv.conf"
        ),
    ] = None,
    loglevel: Annotated[LogLevels, typer.Option(case_sensitive=False)] = LogLevels.INFO,
):
    logging.basicConfig(level=getattr(logging, loglevel))
    if nameservers:
        resolver.nameservers = nameservers.split(",")
    if not is_dnssec_supported():
        raise RuntimeError(
            "DNS resolver is not DNSSEC capable or timed out. Please use a different one."
        )
    run_server(host, port, handler=Handler)
