"""Bulk lookup example.

Bulk lookup is available on the Business and Unlimited plans only.
The library uses the GET / comma-separated form of the bulk endpoint:

    https://ipwhois.pro/bulk/IP1,IP2,IP3?key=...

Up to 100 IP addresses can be passed in a single call. Each address
counts as one credit.
"""

from __future__ import annotations

import sys

from ipwhois import IPWhois


ipwhois = IPWhois("YOUR_API_KEY")

ips = [
    "8.8.8.8",
    "1.1.1.1",
    "208.67.222.222",
    "2c0f:fb50:4003::",     # IPv6 is fine too -- mix freely
]

results = ipwhois.bulk_lookup(ips, lang="en", security=True)

# Whole-batch failure (network down, bad API key, rate limit, ...) -- the
# response is a single error dict instead of a list of per-IP results.
if isinstance(results, dict) and results.get("success") is False:
    print(
        "Bulk request failed: {msg} (HTTP {status})".format(
            msg=results.get("message", "unknown"),
            status=results.get("http_status", 0),
        ),
        file=sys.stderr,
    )
    sys.exit(1)

assert isinstance(results, list)  # for type checkers

for row in results:
    if row.get("success") is False:
        # Per-IP errors (e.g. "Invalid IP address", "Reserved range") are
        # returned inline. The rest of the batch is still usable.
        print(
            "[skip] {ip} -- {msg}".format(
                ip=row.get("ip", "?"),
                msg=row.get("message", "error"),
            )
        )
        continue

    print(
        "{ip:<18s} {flag} {cc:<4s} {isp}".format(
            ip=row["ip"],
            flag=row.get("flag", {}).get("emoji", "  "),
            cc=row.get("country_code", ""),
            isp=row.get("connection", {}).get("isp", ""),
        )
    )
