"""Basic single-IP lookup examples."""

from __future__ import annotations

import sys

from ipwhois import IPWhois


# -----------------------------------------------------------------------
# 1) Free plan -- no API key, ~1 request/second per client IP.
# -----------------------------------------------------------------------
ipwhois = IPWhois()

info = ipwhois.lookup("8.8.8.8")

# All errors -- invalid IP, network failure, bad options, ... -- come back
# here with success == False. The library never raises.
if not info["success"]:
    print(f"Lookup failed: {info.get('message', 'unknown')}", file=sys.stderr)
    sys.exit(1)

print(
    "{ip}  {flag}  ({country}, {city})".format(
        ip=info["ip"],
        flag=info.get("flag", {}).get("emoji", ""),
        country=info.get("country", "unknown"),
        city=info.get("city", "unknown"),
    )
)


# -----------------------------------------------------------------------
# 2) Look up the caller's own IP -- pass nothing (or None).
# -----------------------------------------------------------------------
me = ipwhois.lookup()
if me["success"]:
    print(f"My IP: {me['ip']} -- {me['country']}")


# -----------------------------------------------------------------------
# 3) Paid plan -- supply the API key.
# -----------------------------------------------------------------------
paid = IPWhois("YOUR_API_KEY")

info = paid.lookup(
    "1.1.1.1",
    lang="en",                                          # localised country/city/...
    fields=["success", "country", "city", "connection.isp", "flag.emoji"],
    security=True,                                      # include proxy/vpn/tor flags
    rate=True,                                          # include rate-limit info
)

print(info)
