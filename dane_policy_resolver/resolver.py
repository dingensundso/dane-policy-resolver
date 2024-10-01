import logging
from typing import List

import dns.exception
import dns.flags
import dns.rdataclass
import dns.rdatatype
import dns.rdtypes
import dns.rdtypes.ANY.MX
import dns.rdtypes.ANY.TLSA
import dns.resolver

from . import server

logger = logging.getLogger(__name__)

resolver = dns.resolver.Resolver()
resolver.use_edns(0, dns.flags.DO, 1232)
resolver.flags = dns.flags.AD | dns.flags.RD


def has_dane_record(domain: str, timeout: int = 10) -> bool:
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
    return False


def get_mx_records(domain: str, timeout: int = 10) -> List[dns.rdtypes.ANY.MX.MX]:
    try:
        result = resolver.resolve(
            domain,
            dns.rdatatype.MX,
            dns.rdataclass.IN,
            lifetime=timeout,
        )
        return sorted(list(result), key=lambda r: r.preference)
    except Exception as e:
        logger.error(f"Failed to get MX record for {domain}: {e}")
        return []


def is_dnssec_supported() -> bool:
    logger.info("Checking first reachable nameserver for DNSSEC support.")
    try:
        result = resolver.resolve("isc.org", lifetime=5)
        return result.response.flags & dns.flags.AD != 0
    except dns.exception.Timeout:
        logger.error("DNS timeout while checking for DNSSEC support")
    return False


class Handler(server.RequestHandler):
    def handle_data(self, data: bytes) -> None:
        conn = self.request
        try:
            cmd, key = data.split()
            domain = key.decode()
            if cmd == b"get":
                for mx_record in get_mx_records(domain):
                    mx = str(mx_record)
                    if has_dane_record(mx):
                        logger.info("Found TLSA record for %s (%s)" % (mx, domain))
                        conn.sendall(b"200 dane-only\n")
                        return
                    else:
                        logger.debug("No TLSA record found for %s (%s)" % (mx, domain))
                logger.info("No TLSA record found for %s" % domain)
                conn.sendall(b"500 no dane record found\n")
            else:
                logger.error("unknown command: {!r}".format(data))
                conn.sendall(b"500 unknown command\n")
        except ValueError:
            logger.error("Received malformed data: {!r}".format(data))
            conn.sendall(b"500 malformed data\n")
