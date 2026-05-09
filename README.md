# ipwhois-python

[![PyPI Version](https://img.shields.io/pypi/v/ipwhois-python.svg?v=1)](https://pypi.org/project/ipwhois-python/)
[![Python Versions](https://img.shields.io/pypi/pyversions/ipwhois-python.svg?v=1)](https://pypi.org/project/ipwhois-python/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?v=1)](LICENSE)

Official, dependency-free Python client for the [ipwhois.io](https://ipwhois.io) IP Geolocation API.

- ✅ Single and bulk IP lookups (IPv4 and IPv6)
- ✅ Works with both the **Free** and **Paid** plans
- ✅ HTTPS by default
- ✅ Localisation, field selection, threat detection, rate info
- ✅ Never raises — all errors returned as `success: False` dicts
- ✅ No external dependencies — only the Python standard library
- ✅ Python 3.8+

## Installation

```bash
pip install ipwhois-python
```

## Free vs Paid plan

The same `IPWhois` class is used for both plans. The only difference is whether
you pass an API key:

- **Free plan** — create the client **without arguments**. No API key, no
  signup required. Suitable for low-traffic and non-commercial use.
- **Paid plan** — create the client **with your API key** from
  <https://ipwhois.io>. Higher limits, plus access to bulk lookups and
  threat-detection data.

```python
from ipwhois import IPWhois

free = IPWhois()                 # Free plan — no API key
paid = IPWhois("YOUR_API_KEY")   # Paid plan — with API key
```

Everything else (`lookup()`, options, error handling) is identical.

## Quick start — Free plan (no API key)

```python
from ipwhois import IPWhois

ipwhois = IPWhois()  # no API key

info = ipwhois.lookup("8.8.8.8")

print(info["country"], info["flag"]["emoji"])
# → United States 🇺🇸

print(f"{info['city']}, {info['region']}")
# → Mountain View, California
```

## Quick start — Paid plan (with API key)

Get an API key at <https://ipwhois.io> and pass it to the constructor:

```python
from ipwhois import IPWhois

ipwhois = IPWhois("YOUR_API_KEY")  # with API key

info = ipwhois.lookup("8.8.8.8")

print(info["country"], info["flag"]["emoji"])
# → United States 🇺🇸

print(f"{info['city']}, {info['region']}")
# → Mountain View, California
```

> ℹ️ Pass nothing to look up your own public IP: `ipwhois.lookup()` — works
> on both plans.

## Lookup options

Every option below can be passed per call as a keyword argument, or set once
on the client as a default.

| Option       | Type    | Plans needed         | Description                                                            |
| ------------ | ------- | -------------------- | ---------------------------------------------------------------------- |
| `lang`       | str     | Free + Paid          | One of: `en`, `ru`, `de`, `es`, `pt-BR`, `fr`, `zh-CN`, `ja`           |
| `fields`     | list    | Free + Paid          | Restrict the response to specific fields (e.g. `["country", "city"]`)  |
| `output`     | str     | Free + Paid          | `json` (default), `xml`, `csv`                                         |
| `rate`       | bool    | Basic and above      | Include the `rate` block (`limit`, `remaining`)                        |
| `security`   | bool    | Business and above   | Include the `security` block (proxy/vpn/tor/hosting)                   |

### Setting defaults once

If you make many calls with the same options, set them once and forget:

```python
# Free plan
ipwhois = (
    IPWhois()
    .set_language("en")
    .set_fields(["country", "city", "flag.emoji"])
    .set_timeout(8)
)

ipwhois.lookup("8.8.8.8")                  # uses all of the above
ipwhois.lookup("1.1.1.1", lang="de")       # per-call options override defaults
```

```python
# Paid plan
ipwhois = (
    IPWhois("YOUR_API_KEY")
    .set_language("en")
    .set_fields(["country", "city", "flag.emoji"])
    .set_timeout(8)
)

ipwhois.lookup("8.8.8.8")                  # uses all of the above
ipwhois.lookup("1.1.1.1", lang="de")       # per-call options override defaults
```

> ℹ️ Paid plans additionally support `set_security(True)` (Business+) and
> `set_rate(True)` (Basic+). See the table above for what's available where.

## HTTPS encryption

By default, all requests are sent over HTTPS. If you need to disable it (for
example, in environments without an up-to-date CA bundle), pass `ssl=False`
to the constructor:

```python
from ipwhois import IPWhois

# Free plan
ipwhois = IPWhois(ssl=False)
```

```python
from ipwhois import IPWhois

# Paid plan
ipwhois = IPWhois("YOUR_API_KEY", ssl=False)
```

> ℹ️ HTTPS is strongly recommended for production traffic — your API key is
> sent in the query string and would otherwise travel in clear text.

## Bulk lookup (Paid plan only)

The bulk endpoint sends **up to 100 IPs** in a single GET request. Each
address counts as one credit. Available on the **Business** and **Unlimited**
plans.

```python
from ipwhois import IPWhois

ipwhois = IPWhois("YOUR_API_KEY")

results = ipwhois.bulk_lookup([
    "8.8.8.8",
    "1.1.1.1",
    "208.67.222.222",
    "2c0f:fb50:4003::",     # IPv6 is fine — mix freely
])

for row in results:
    if row.get("success") is False:
        # Per-IP errors (e.g. "Invalid IP address") are returned inline,
        # they do NOT raise — the rest of the batch is still usable.
        print(f"skip {row['ip']}: {row['message']}")
        continue
    print(f"{row['ip']} → {row['country']}")
```

> ℹ️ Bulk requires an API key. Calling `bulk_lookup()` without one will fail
> at the API level.

## Error handling

**The library never raises.** Every failure — invalid IP, bad API key, rate
limit, network outage, bad options — comes back inside the response dict
with `success` set to `False` and a `message`. Just check
`info["success"]` after every call:

```python
info = ipwhois.lookup("8.8.8.8")

if not info["success"]:
    print(f"Lookup failed: {info['message']}")
    return

print(info["country"])
```

This means an outage of the ipwhois.io API (or of your machine's DNS,
connection, etc.) will never surface as an unhandled exception in your
application — you decide how to react.

### Error response fields

Every error response contains `success: False` and a `message`. Some errors
include extra fields you can branch on:

| Field          | When it's present                                                            |
| -------------- | ---------------------------------------------------------------------------- |
| `error_type`   | `'network'` or `'invalid_argument'` — for non-API errors                     |
| `http_status`  | On HTTP 4xx / 5xx responses                                                  |
| `retry_after`  | On HTTP 429 if the API sent a `Retry-After` header                           |

```python
import time

info = ipwhois.lookup("8.8.8.8")

if not info["success"]:
    if info.get("http_status") == 429:
        time.sleep(info.get("retry_after", 60))
        # ...retry

    if info.get("error_type") == "network":
        # DNS failure, connection refused, timeout, ...
        pass

    print(f"Error: {info['message']}")
```

## Response shape

A successful response includes (depending on your plan and selected options):

```jsonc
{
    "ip": "8.8.4.4",
    "success": true,
    "type": "IPv4",
    "continent": "North America",
    "continent_code": "NA",
    "country": "United States",
    "country_code": "US",
    "region": "California",
    "region_code": "CA",
    "city": "Mountain View",
    "latitude": 37.3860517,
    "longitude": -122.0838511,
    "is_eu": false,
    "postal": "94039",
    "calling_code": "1",
    "capital": "Washington D.C.",
    "borders": "CA,MX",
    "flag": {
        "img": "https://cdn.ipwhois.io/flags/us.svg",
        "emoji": "🇺🇸",
        "emoji_unicode": "U+1F1FA U+1F1F8"
    },
    "connection": {
        "asn": 15169,
        "org": "Google LLC",
        "isp": "Google LLC",
        "domain": "google.com"
    },
    "timezone": {
        "id": "America/Los_Angeles",
        "abbr": "PDT",
        "is_dst": true,
        "offset": -25200,
        "utc": "-07:00",
        "current_time": "2026-05-08T14:31:48-07:00"
    },
    "currency": {
        "name": "US Dollar",
        "code": "USD",
        "symbol": "$",
        "plural": "US dollars",
        "exchange_rate": 1
    },
    "security": {
        "anonymous": false,
        "proxy": false,
        "vpn": false,
        "tor": false,
        "hosting": false
    },
    "rate": {
        "limit": 250000,
        "remaining": 50155
    }
}
```

For the full field reference, see the [official documentation](https://ipwhois.io/documentation).

An **error** response looks like:

```jsonc
{
    "success": false,
    "message": "Invalid IP address",
    "http_status": 400          // present for HTTP 4xx / 5xx
    // "retry_after": 60        // additionally present on HTTP 429 if the API sent a Retry-After header
    // "error_type": "network"  // present for non-API errors: 'network', 'invalid_argument'
}
```

## Requirements

- Python **3.8** or newer
- No third-party dependencies — only the standard library (`urllib`, `json`)

## Contributing

Issues and pull requests are welcome on
[GitHub](https://github.com/IPWhois/ipwhois-python).

## License

[MIT](LICENSE) © ipwhois.io
