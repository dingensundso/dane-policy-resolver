from typing import Annotated, Optional
import logging
from enum import Enum
import typer

from .server import run_server
from .resolver import Handler, resolver

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
    if nameservers:
        resolver.nameservers = nameservers.split(",")
    logging.basicConfig(level=getattr(logging, loglevel))
    run_server(host, port, handler=Handler)
