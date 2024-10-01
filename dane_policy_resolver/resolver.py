import logging
import typer
from typing import Annotated, Optional

import dns.resolver
import dns.exception
import dns.flags
import dns.rdtypes
import dns.rdatatype
import dns.rdataclass

from . import server

logger = logging.getLogger("dane-policy-resolver")

resolver = dns.resolver.Resolver()
resolver.use_edns(0, dns.flags.DO, 1232)
resolver.flags = dns.flags.AD | dns.flags.RD


def has_dane_record(domain, timeout=10):
    """Checks whether domain has a dane record

    Copyright 2016 All Mailu contributors at the date.
    See the LICENSE.md file at the top-level directory of this distribution and
    https://github.com/Mailu/Mailu/blob/master/LICENSE.md
    """
    try:
        result = resolver.resolve(
            f"_25._tcp.{domain}",
            dns.rdatatype.TLSA,
            dns.rdataclass.IN,
            lifetime=timeout,
        )
        if result.response.flags & dns.flags.AD:
            for record in result:
                if isinstance(record, dns.rdtypes.ANY.TLSA.TLSA):
                    if (
                        record.usage in [2, 3]
                        and record.selector in [0, 1]
                        and record.mtype in [0, 1, 2]
                    ):
                        return True
    except dns.resolver.NoNameservers:
        # If the DNSSEC data is invalid and the DNS resolver is DNSSEC enabled
        # we will receive this non-specific exception. The safe behaviour is to
        # accept to defer the email.
        logger.warning(
            f"Unable to lookup the TLSA record for {domain}. Is the DNSSEC zone okay on https://dnsviz.net/d/{domain}/dnssec/?"
        )
        return True
    except dns.exception.Timeout:
        logger.warning(
            f"Timeout while resolving the TLSA record for {domain} ({timeout}s)."
        )
    except (dns.resolver.NXDOMAIN, dns.name.EmptyLabel):
        pass  # this is expected, not TLSA record is fine
    except Exception as e:
        logger.info(f"Error while looking up the TLSA record for {domain} {e}")
        pass


class Handler(server.RequestHandler):
    def handle_data(self, data):
        conn = self.request
        try:
            cmd, key = data.split()
            if cmd == b"get":
                if has_dane_record(key.decode()):
                    logger.debug("Found TLSA record for %s" % key)
                    conn.sendall(b"200 dane-only\n")
                else:
                    logger.debug("No TLSA record found for %s" % key)
                    conn.sendall(b"500 no dane record found\n")
            else:
                logger.error("unknown command: {}".format(data))
                conn.sendall(b"500 unknown command\n")
        except ValueError:
            logger.error("Received malformed data: {}".format(data))
            conn.sendall(b"500 malformed data\n")


def main(
    host: str = "localhost",
    port: int = 8460,
    nameservers: Annotated[
        Optional[str],
        typer.Option(
            help="comma-seperated list of nameservers. default uses /etc/resolv.conf"
        ),
    ] = None,
):
    if nameservers:
        resolver.nameservers = nameservers.split(",")
    logging.basicConfig(level=logging.DEBUG)
    server.run_server(host, port, handler=Handler)
