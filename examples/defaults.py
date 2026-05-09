"""Setting client-wide defaults.

If you make many requests with the same options, set them once on the
client. Per-call options always override the defaults.
"""

from __future__ import annotations

import sys

from ipwhois import IPWhois


ipwhois = (
    IPWhois("YOUR_API_KEY")
    .set_language("en")
    .set_fields(["success", "country", "city", "flag.emoji", "connection.isp"])
    .set_security(True)
    .set_timeout(8)
)


def show(label: str, info: dict) -> None:
    """Print a row, or the API/network error if the call failed."""
    if not info["success"]:
        print(f"{label}: {info.get('message', 'unknown error')}", file=sys.stderr)
        return
    flag = info.get("flag", {}).get("emoji", "")
    print(f"{label}: {info.get('country', '?')} / {info.get('city', '?')} {flag}")


# Both calls below will use lang=en, the field whitelist, and security=1.
google = ipwhois.lookup("8.8.8.8")
cf     = ipwhois.lookup("1.1.1.1")

show("8.8.8.8", google)
show("1.1.1.1", cf)

# One-off override -- this single call uses German instead of English.
de_only = ipwhois.lookup("8.8.4.4", lang="de")
show("8.8.4.4 (de)", de_only)
