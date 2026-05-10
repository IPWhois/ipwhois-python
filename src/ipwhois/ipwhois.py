"""Python client for the ipwhois.io IP Geolocation API.

Quick start
-----------
    from ipwhois import IPWhois

    # Free plan (no API key, ~1 request/second per client IP)
    ipwhois = IPWhois()
    info    = ipwhois.lookup("8.8.8.8")

    # Paid plan (with API key, higher limits, bulk, security data, ...)
    ipwhois = IPWhois("YOUR_API_KEY")
    info    = ipwhois.lookup("8.8.8.8", lang="en", security=True)

    # Bulk lookup -- up to 100 IPs in one call (paid only)
    rows = ipwhois.bulk_lookup(["8.8.8.8", "1.1.1.1", "208.67.222.222"])

    # HTTPS is enabled by default. Pass ssl=False to fall back to HTTP.

Error handling
--------------
The library never raises. All errors -- invalid input, network failure,
API-level errors (bad IP, bad key, rate limit, ...) -- are returned in the
response dict with ``success`` set to ``False`` and a ``message``. Just check
``info["success"]`` after every call.
"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterable, List, Optional, Union

__all__ = ["IPWhois"]

# Public type alias: a single API response (lookup or whole-batch error).
Response = Dict[str, Any]
# Public type alias: a bulk response -- list on success, error dict otherwise.
BulkResponse = Union[List[Response], Response]


class IPWhois:
    """Client for the ipwhois.io IP Geolocation API.

    The same class is used for both the Free and Paid plans -- the only
    difference is whether you pass an API key. See module docstring for
    a quick start.

    The library never raises. Every failure -- invalid IP, bad API key, rate
    limit, network outage, bad options -- comes back inside the response dict
    with ``success`` set to ``False`` and a ``message``.
    """

    #: Library version, used in the default User-Agent header.
    VERSION: str = "1.2.0"

    #: Free-plan endpoint host (used when no API key is provided).
    HOST_FREE: str = "ipwho.is"

    #: Paid-plan endpoint host (used when an API key is provided).
    HOST_PAID: str = "ipwhois.pro"

    #: Maximum number of IP addresses allowed in a single bulk request.
    BULK_LIMIT: int = 100

    #: Languages supported by the ``lang`` parameter.
    SUPPORTED_LANGUAGES: tuple = (
        "en",
        "ru",
        "de",
        "es",
        "pt-BR",
        "fr",
        "zh-CN",
        "ja",
    )

    def __init__(self, api_key: Optional[str] = None, **options: Any) -> None:
        """Create a new client.

        :param api_key: Your ipwhois.io API key. Omit for the free plan.
        :param options: Optional defaults applied to every request. Recognised
            keys: ``lang``, ``fields``, ``security``, ``rate``, ``ssl``,
            ``timeout``, ``connect_timeout``, ``user_agent``.
        """
        self._api_key: Optional[str] = api_key
        self._user_agent: str = str(
            options.pop("user_agent", f"ipwhois-python/{self.VERSION}")
        )
        self._timeout: int = _coerce_positive_int(options.pop("timeout", 10), 10)
        self._connect_timeout: int = _coerce_positive_int(
            options.pop("connect_timeout", 5), 5
        )
        self._ssl: bool = bool(options.pop("ssl", True))

        # Anything left is a request-level default (lang, fields, ...).
        self._defaults: Dict[str, Any] = options

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #

    def lookup(self, ip: Optional[str] = None, **options: Any) -> Response:
        """Look up information for a single IP address.

        Pass ``None`` (or call without arguments) to look up the caller's own
        public IP, as documented at https://ipwhois.io/documentation.

        The library never raises -- check ``result["success"]`` after every
        call.

        :param ip: IPv4 or IPv6 address. ``None`` (default) = current IP.
        :param options: Per-call options: ``lang``, ``fields``,
            ``security`` (bool), ``rate`` (bool).
        :returns: Decoded JSON response. On any error (API, network, bad
            input) the dict contains ``success`` set to ``False`` and a
            ``message``. The library never raises.
        """
        error = self._validate_options(options)
        if error is not None:
            return error

        path = "/" + urllib.parse.quote(ip, safe="") if ip is not None else "/"
        url = self._build_url(path, options)

        result = self._request(url)
        # Single lookup always parses to a dict in practice -- but in the
        # unlikely case the API returns a list, normalise to an error dict
        # so the caller's `result["success"]` check stays valid.
        if isinstance(result, list):
            return {
                "success": False,
                "message": "Unexpected list response from single lookup endpoint.",
                "error_type": "api",
            }
        return result

    def bulk_lookup(
        self, ips: Iterable[str], **options: Any
    ) -> BulkResponse:
        """Look up information for multiple IP addresses in a single request.

        Uses the GET / comma-separated form documented at
        https://ipwhois.io/documentation/bulk -- up to 100 addresses per call.
        Each address counts as one credit.

        Available on the Business and Unlimited plans only.

        Per-IP errors are returned inline with ``success`` set to ``False``
        for the affected entry; the rest of the batch is still usable. If
        the whole call fails, the response is a single error dict with
        ``success`` set to ``False`` instead of a list.

        :param ips: Up to 100 IPv4/IPv6 addresses (mixable).
        :param options: Per-call options (same keys as :meth:`lookup`).
        :returns: List of per-IP results on success; a single error dict on
            whole-batch failure. The library never raises.
        """
        # Strings and bytes are iterable in Python -- without this guard,
        # bulk_lookup("8.8.8.8") would lookup each character. Reject them
        # explicitly with a helpful message.
        if ips is None:
            return {
                "success": False,
                "message": "Bulk lookup requires an iterable of IP addresses.",
                "error_type": "invalid_argument",
            }
        if isinstance(ips, (str, bytes, bytearray)):
            return {
                "success": False,
                "message": (
                    "Bulk lookup requires an iterable of IP strings, not a "
                    "single string. Use lookup() for a single IP."
                ),
                "error_type": "invalid_argument",
            }

        try:
            ip_list = [str(ip) for ip in ips]
        except TypeError:
            return {
                "success": False,
                "message": "Bulk lookup requires an iterable of IP addresses.",
                "error_type": "invalid_argument",
            }

        if not ip_list:
            return {
                "success": False,
                "message": "Bulk lookup requires at least one IP address.",
                "error_type": "invalid_argument",
            }
        if len(ip_list) > self.BULK_LIMIT:
            return {
                "success": False,
                "message": (
                    f"Bulk lookup accepts at most {self.BULK_LIMIT} IP "
                    f"addresses per call, got {len(ip_list)}."
                ),
                "error_type": "invalid_argument",
            }

        error = self._validate_options(options)
        if error is not None:
            return error

        # The API accepts addresses joined by commas -- the commas themselves
        # must NOT be URL-encoded, otherwise the path is misinterpreted.
        joined = ",".join(urllib.parse.quote(ip, safe="") for ip in ip_list)
        url = self._build_url("/bulk/" + joined, options)

        return self._request(url)

    # -- Fluent setters ------------------------------------------------- #

    def set_language(self, lang: str) -> "IPWhois":
        """Set the default language used when none is supplied per call.

        :param lang: One of :attr:`SUPPORTED_LANGUAGES`.
        """
        self._defaults["lang"] = lang
        return self

    def set_fields(
        self, fields: Union[str, Iterable[str], None]
    ) -> "IPWhois":
        """Restrict every response to a fixed set of fields by default.

        Include ``"success"`` in the list if you rely on ``info["success"]``
        for error checking -- when ``fields`` is set, the API only returns
        the fields you ask for.

        :param fields: An iterable of field names, e.g.
            ``["success", "country", "city", "flag.emoji"]``. A pre-joined
            comma-separated string is also accepted and passed through
            unchanged. Pass ``None`` to clear any previously-set default.
        """
        # Strings are iterable in Python, so list("country,city") would
        # explode into individual characters. Keep strings as strings.
        # `None` clears the default (consistent with "never raises": calling
        # set_fields(None) shouldn't blow up). Anything that's not iterable
        # at all is stringified rather than raising.
        if fields is None:
            self._defaults.pop("fields", None)
        elif isinstance(fields, str):
            self._defaults["fields"] = fields
        else:
            try:
                self._defaults["fields"] = list(fields)
            except TypeError:
                self._defaults["fields"] = str(fields)
        return self

    def set_security(self, enabled: bool) -> "IPWhois":
        """Enable or disable threat-detection data on every call by default."""
        self._defaults["security"] = bool(enabled)
        return self

    def set_rate(self, enabled: bool) -> "IPWhois":
        """Enable or disable the ``rate`` block in responses by default."""
        self._defaults["rate"] = bool(enabled)
        return self

    def set_timeout(self, seconds: Any) -> "IPWhois":
        """Set the per-request total timeout in seconds (default: 10).

        Bad values (non-numeric, negative) silently fall back to the default,
        in keeping with the library's "never raises" contract.
        """
        self._timeout = _coerce_positive_int(seconds, self._timeout)
        return self

    def set_connect_timeout(self, seconds: Any) -> "IPWhois":
        """Set the connection timeout in seconds (default: 5).

        Note: Python's :mod:`urllib` exposes a single timeout that covers
        both the connect and read phases. This value is stored for API
        parity with the PHP client; the effective ceiling for the whole
        request is :meth:`set_timeout`.

        Bad values (non-numeric, negative) silently fall back to the
        previous value, in keeping with the library's "never raises"
        contract.
        """
        self._connect_timeout = _coerce_positive_int(
            seconds, self._connect_timeout
        )
        return self

    def set_user_agent(self, user_agent: str) -> "IPWhois":
        """Override the User-Agent header sent with every request."""
        self._user_agent = str(user_agent)
        return self

    # ------------------------------------------------------------------ #
    # Internals                                                          #
    # ------------------------------------------------------------------ #

    def _validate_options(self, options: Dict[str, Any]) -> Optional[Response]:
        """Validate per-call options.

        :returns: An error dict on the first invalid option, or ``None`` if
            everything looks OK.
        """
        merged = {**self._defaults, **options}

        lang = merged.get("lang")
        if lang is not None and lang not in self.SUPPORTED_LANGUAGES:
            return {
                "success": False,
                "message": (
                    f'Unsupported language "{lang}". Supported: '
                    f"{', '.join(self.SUPPORTED_LANGUAGES)}."
                ),
                "error_type": "invalid_argument",
            }

        return None

    def _build_url(self, path: str, options: Dict[str, Any]) -> str:
        """Build the full URL for a given path + options."""
        host = self.HOST_PAID if self._api_key is not None else self.HOST_FREE

        # Per-call options win over defaults.
        merged = {**self._defaults, **options}

        query: List[tuple] = []

        if self._api_key is not None:
            query.append(("key", self._api_key))

        if "lang" in merged and merged["lang"] is not None:
            query.append(("lang", str(merged["lang"])))

        if "fields" in merged and merged["fields"] is not None:
            fields = merged["fields"]
            if isinstance(fields, (list, tuple)):
                fields = ",".join(str(f) for f in fields)
            query.append(("fields", str(fields)))

        if merged.get("security"):
            query.append(("security", "1"))

        if merged.get("rate"):
            query.append(("rate", "1"))

        scheme = "https" if self._ssl else "http"
        url = f"{scheme}://{host}{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query)

        return url

    def _request(self, url: str) -> Union[Response, List[Any]]:
        """Perform a GET request and return the decoded JSON body.

        On any error returns an error dict with ``success`` set to ``False``;
        on bulk success returns the parsed JSON list directly.
        """
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": self._user_agent,
            },
            method="GET",
        )

        status: int
        body: str
        headers: Dict[str, str]

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                status = int(getattr(resp, "status", resp.getcode()))
                headers = {k.lower(): v for k, v in resp.headers.items()}
                raw = resp.read()
                body = raw.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            # 4xx / 5xx -- read the body and normalise into an error dict
            # below, the same way a 2xx response with success=false is.
            status = int(e.code)
            try:
                headers = {
                    k.lower(): v for k, v in (e.headers or {}).items()
                }
            except Exception:
                headers = {}
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
        except urllib.error.URLError as e:
            return {
                "success": False,
                "message": f"Network error: {e.reason}",
                "error_type": "network",
            }
        except socket.timeout:
            return {
                "success": False,
                "message": (
                    f"Network error: timed out after {self._timeout}s"
                ),
                "error_type": "network",
            }
        except (TimeoutError, OSError) as e:
            return {
                "success": False,
                "message": f"Network error: {e}",
                "error_type": "network",
            }

        decoded: Any = None
        if body:
            try:
                decoded = json.loads(body)
            except json.JSONDecodeError:
                # The ipwhois API always returns JSON. A non-JSON body means
                # something went wrong upstream (gateway error page, captive
                # portal, hijacked response, ...) -- synthesise an error dict
                # so the caller can handle it the same way as a normal API
                # error.
                snippet = " ".join(body.split())
                if len(snippet) > 200:
                    snippet = snippet[:200] + "\u2026"
                return {
                    "success": False,
                    "message": (
                        f"Invalid JSON returned by ipwhois API "
                        f"(HTTP {status}): {snippet}"
                    ),
                    "http_status": status,
                    "error_type": "api",
                }

        if not isinstance(decoded, (dict, list)):
            decoded = {} if decoded is None else {"value": decoded}

        # For HTTP errors, normalise into a `success: False` dict so the
        # caller doesn't have to inspect HTTP status separately.
        if status >= 400:
            if isinstance(decoded, dict):
                if decoded.get("success") is False:
                    # The API already shaped the error correctly -- just enrich it.
                    decoded["http_status"] = status
                else:
                    message = str(
                        decoded.get(
                            "message", f"HTTP {status} returned by ipwhois API"
                        )
                    )
                    decoded = {
                        "success": False,
                        "message": message,
                        "http_status": status,
                    }
            else:
                # List response with error status -- wrap as an error dict.
                decoded = {
                    "success": False,
                    "message": f"HTTP {status} returned by ipwhois API",
                    "http_status": status,
                }

            # `Retry-After` is only emitted by the free-plan endpoint
            # (ipwho.is); the paid endpoint (ipwhois.pro) does not send the
            # header, so don't try to read it there.
            if (
                status == 429
                and self._api_key is None
                and "retry-after" in headers
            ):
                try:
                    decoded["retry_after"] = int(headers["retry-after"])
                except (TypeError, ValueError):
                    pass

        # Tag every API-shaped error (`success: False` returned by the API,
        # on any HTTP status) with `error_type: 'api'` so callers can branch
        # on the category alongside the non-API codes ('network',
        # 'environment', 'invalid_argument'). HTTP 2xx + success=false bodies
        # (e.g. "Invalid IP address", "Reserved range") are otherwise passed
        # through untouched.
        if (
            isinstance(decoded, dict)
            and decoded.get("success") is False
            and "error_type" not in decoded
        ):
            decoded["error_type"] = "api"

        # For HTTP 2xx with `success: false` (e.g. "Invalid IP address",
        # "Reserved range") we just pass the body through -- it is already
        # shaped correctly by the API.

        return decoded


def _coerce_positive_int(value: Any, default: int) -> int:
    """Coerce ``value`` to a positive int, falling back to ``default``.

    Mirrors PHP's lenient ``(int)`` cast so that a stray ``"foo"`` passed
    via constructor kwargs or :meth:`IPWhois.set_timeout` doesn't blow up
    the whole client. ``None``, non-numeric strings, ``True``/``False``
    edge cases, negative numbers and zero all map to ``default``.
    """
    if value is None or isinstance(value, bool):
        return default
    try:
        coerced = int(value)
    except (TypeError, ValueError):
        return default
    if coerced <= 0:
        return default
    return coerced

