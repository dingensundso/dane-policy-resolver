# dane-policy-resolver
`dane-policy-resolver` is a program for postfix which can be used with [`master`](https://www.postfix.org/master.8.html) and [`spawn`](https://www.postfix.org/spawn.8.html) as [`tcp_table`](https://www.postfix.org/tcp_table.5.html) for [`smtp_tls_policy_maps`](http://www.postfix.org/postconf.5.html#smtp_tls_policy_maps).
It can make the usage of [`postfix-mta-sts-resolver`](https://github.com/Snawoot/postfix-mta-sts-resolver) compliant with [RFC 8561, 2](https://www.rfc-editor.org/rfc/rfc8461#section-2).

`dane-policy-resolver` returns `dane-only` if the given hostname has a TLSA-record.

## Credits
Almost all of the code comes from [Mailu](https://github.com/Mailu/Mailu)'s [util.py](https://github.com/Mailu/Mailu/blob/master/core/admin/mailu/utils.py#L54). Thank you to all contributors!

## Usage
Use `dane-policy-resolver --help` to view command line options.
Make sure to use a **DNSSEC-enabled** resolver!

After starting it (e.g. with systemd) we can add the address (e.g. `127.0.0.1:8460`) as [`tcp_table`](https://www.postfix.org/tcp_table.5.html) to [`smtp_tls_policy_maps`](http://www.postfix.org/postconf.5.html#smtp_tls_policy_maps) in `/etc/postfix/main.cf`:

    smtp_tls_policy_maps = tcp:127.0.0.1:8460

If you are using [`postfix-mta-sts-resolver`](https://github.com/Snawoot/postfix-mta-sts-resolver) as well, you have to put it after `dane-policy-resolver`:

    smtp_tls_policy_maps = tcp:127.0.0.1:8460,socketmap:inet:127.0.0.1:8461:postfix
