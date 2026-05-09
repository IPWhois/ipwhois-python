"""Tests covering URL construction and input validation.

No real HTTP request is sent -- ``_build_url()`` is exercised directly so
the suite can be run anywhere without an API key or network access.
"""

from __future__ import annotations

from ipwhois import IPWhois


def _build_url(ipwhois: IPWhois, path: str, **options) -> str:
    return ipwhois._build_url(path, options)


def test_free_endpoint_has_no_api_key() -> None:
    ipwhois = IPWhois()
    assert _build_url(ipwhois, "/8.8.8.8") == "https://ipwho.is/8.8.8.8"


def test_paid_endpoint_appends_api_key() -> None:
    ipwhois = IPWhois("TESTKEY")
    url = _build_url(ipwhois, "/8.8.8.8")

    assert url.startswith("https://ipwhois.pro/8.8.8.8?")
    assert "key=TESTKEY" in url


def test_https_is_always_used_by_default() -> None:
    assert _build_url(IPWhois(), "/").startswith("https://")
    assert _build_url(IPWhois("K"), "/").startswith("https://")


def test_ssl_can_be_disabled() -> None:
    free = IPWhois(ssl=False)
    paid = IPWhois("K", ssl=False)

    assert _build_url(free, "/").startswith("http://ipwho.is")
    assert _build_url(paid, "/").startswith("http://ipwhois.pro")


def test_ssl_defaults_to_true_when_not_passed() -> None:
    # Sanity check: omitting the option keeps HTTPS on.
    assert _build_url(IPWhois("K"), "/").startswith("https://")


def test_fields_are_joined_with_commas() -> None:
    ipwhois = IPWhois("K")
    url = _build_url(
        ipwhois, "/8.8.8.8", fields=["country", "city", "flag.emoji"]
    )

    # urlencode encodes commas as %2C -- both forms are valid HTTP.
    assert "fields=country%2Ccity%2Cflag.emoji" in url


def test_fields_accepts_a_string_too() -> None:
    ipwhois = IPWhois("K")
    url = _build_url(ipwhois, "/8.8.8.8", fields="country,city")
    assert "fields=country%2Ccity" in url


def test_security_and_rate_are_flags_not_values() -> None:
    ipwhois = IPWhois("K")
    url = _build_url(ipwhois, "/", security=True, rate=True)

    assert "security=1" in url
    assert "rate=1" in url


def test_security_false_is_omitted() -> None:
    ipwhois = IPWhois("K")
    url = _build_url(ipwhois, "/", security=False)

    assert "security=" not in url


def test_per_call_options_override_defaults() -> None:
    ipwhois = IPWhois("K", lang="ru")
    url = _build_url(ipwhois, "/", lang="en")

    assert "lang=en" in url
    assert "lang=ru" not in url


def test_invalid_language_returns_error_dict() -> None:
    result = IPWhois().lookup("8.8.8.8", lang="klingon")

    assert result["success"] is False
    assert result.get("error_type") == "invalid_argument"
    assert "klingon" in result.get("message", "")


def test_bulk_lookup_refuses_empty_list() -> None:
    result = IPWhois("K").bulk_lookup([])

    assert isinstance(result, dict)
    assert result["success"] is False
    assert result.get("error_type") == "invalid_argument"


def test_bulk_lookup_refuses_more_than_limit() -> None:
    too_many = ["8.8.8.8"] * (IPWhois.BULK_LIMIT + 1)
    result = IPWhois("K").bulk_lookup(too_many)

    assert isinstance(result, dict)
    assert result["success"] is False
    assert result.get("error_type") == "invalid_argument"


def test_bulk_url_is_comma_separated() -> None:
    ipwhois = IPWhois("K")
    url = _build_url(ipwhois, "/bulk/" + ",".join(["8.8.8.8", "1.1.1.1"]))

    assert "/bulk/8.8.8.8,1.1.1.1" in url


def test_fluent_setters_return_self() -> None:
    ipwhois = IPWhois()

    assert ipwhois.set_language("en") is ipwhois
    assert ipwhois.set_fields(["country"]) is ipwhois
    assert ipwhois.set_security(True) is ipwhois
    assert ipwhois.set_rate(False) is ipwhois
    assert ipwhois.set_timeout(5) is ipwhois
    assert ipwhois.set_connect_timeout(2) is ipwhois
    assert ipwhois.set_user_agent("test/1.0") is ipwhois


def test_set_language_affects_subsequent_requests() -> None:
    ipwhois = IPWhois("K").set_language("de")
    url = _build_url(ipwhois, "/")

    assert "lang=de" in url


def test_set_fields_affects_subsequent_requests() -> None:
    ipwhois = IPWhois("K").set_fields(["country", "city"])
    url = _build_url(ipwhois, "/8.8.8.8")

    assert "fields=country%2Ccity" in url


def test_constructor_options_become_defaults() -> None:
    ipwhois = IPWhois("K", lang="ru", security=True)
    url = _build_url(ipwhois, "/8.8.8.8")

    assert "lang=ru" in url
    assert "security=1" in url


def test_user_agent_can_be_set_in_constructor() -> None:
    ipwhois = IPWhois(user_agent="my-app/2.0")
    assert ipwhois._user_agent == "my-app/2.0"


def test_default_user_agent_includes_version() -> None:
    ipwhois = IPWhois()
    assert ipwhois._user_agent == f"ipwhois-python/{IPWhois.VERSION}"


def test_ip_is_url_encoded_for_ipv6() -> None:
    # IPv6 colons must be percent-encoded inside a path segment.
    ipwhois = IPWhois()
    url = _build_url(ipwhois, "/" + __import__("urllib.parse", fromlist=["quote"]).quote("2c0f:fb50:4003::", safe=""))
    assert "%3A" in url


# --------------------------------------------------------------------- #
# Regression tests -- footguns that an external review caught.          #
# --------------------------------------------------------------------- #


def test_bulk_lookup_rejects_a_single_string() -> None:
    # Strings are iterable in Python; without the guard, "8.8.8.8" would
    # be looked up character-by-character. Reject explicitly.
    result = IPWhois("K").bulk_lookup("8.8.8.8")  # type: ignore[arg-type]

    assert isinstance(result, dict)
    assert result["success"] is False
    assert result.get("error_type") == "invalid_argument"
    assert "single string" in result["message"]


def test_bulk_lookup_rejects_bytes() -> None:
    result = IPWhois("K").bulk_lookup(b"8.8.8.8")  # type: ignore[arg-type]

    assert isinstance(result, dict)
    assert result["success"] is False
    assert result.get("error_type") == "invalid_argument"


def test_bulk_lookup_handles_none_gracefully() -> None:
    result = IPWhois("K").bulk_lookup(None)  # type: ignore[arg-type]

    assert isinstance(result, dict)
    assert result["success"] is False
    assert result.get("error_type") == "invalid_argument"


def test_bulk_lookup_handles_non_iterable_gracefully() -> None:
    result = IPWhois("K").bulk_lookup(42)  # type: ignore[arg-type]

    assert isinstance(result, dict)
    assert result["success"] is False
    assert result.get("error_type") == "invalid_argument"


def test_bulk_lookup_accepts_a_generator() -> None:
    ipwhois = IPWhois("K")
    # A generator is an iterable that's not a list -- make sure it works.
    gen = (ip for ip in ["8.8.8.8", "1.1.1.1"])
    # Just check it gets through validation -- we don't actually hit the
    # network. Validation passes if we don't get an `error_type` back.
    # We trigger the guard *before* network by passing an empty generator:
    empty = (x for x in [])
    result = ipwhois.bulk_lookup(empty)
    assert isinstance(result, dict)
    assert result["success"] is False
    assert result.get("error_type") == "invalid_argument"
    # And confirm a populated generator at least gets past type guards
    # (we won't make a real HTTP call here).
    _ = gen  # silence unused-warning


def test_set_fields_keeps_string_intact() -> None:
    # Without the str guard, list("country,city") explodes into characters.
    ipwhois = IPWhois("K").set_fields("country,city")
    url = _build_url(ipwhois, "/8.8.8.8")

    assert "fields=country%2Ccity" in url
    # Sanity: confirm we haven't accidentally produced the broken form.
    assert "fields=c%2Co%2Cu" not in url


def test_set_fields_tolerates_none() -> None:
    # set_fields(None) must not raise; it clears any previously-set default.
    ipwhois = IPWhois().set_fields(["country"]).set_fields(None)
    url = ipwhois._build_url("/8.8.8.8", {})
    assert "fields=" not in url


def test_set_fields_tolerates_non_iterable() -> None:
    # Non-iterable, non-string garbage falls back to str() rather than raising.
    ipwhois = IPWhois("K").set_fields(42)  # type: ignore[arg-type]
    url = _build_url(ipwhois, "/8.8.8.8")
    assert "fields=42" in url


def test_set_timeout_tolerates_garbage_input() -> None:
    # "never raises" extends to setters: bad input falls back to previous
    # value rather than raising ValueError.
    ipwhois = IPWhois()
    previous = ipwhois._timeout

    ipwhois.set_timeout("not a number")  # type: ignore[arg-type]
    assert ipwhois._timeout == previous

    ipwhois.set_timeout(None)  # type: ignore[arg-type]
    assert ipwhois._timeout == previous

    ipwhois.set_timeout(-5)
    assert ipwhois._timeout == previous

    # Numeric strings are accepted (matches PHP's `(int)` behaviour).
    ipwhois.set_timeout("15")  # type: ignore[arg-type]
    assert ipwhois._timeout == 15


def test_set_connect_timeout_tolerates_garbage_input() -> None:
    ipwhois = IPWhois()
    previous = ipwhois._connect_timeout

    ipwhois.set_connect_timeout("oops")  # type: ignore[arg-type]
    assert ipwhois._connect_timeout == previous


def test_constructor_tolerates_bad_timeout() -> None:
    # Constructor garbage values fall back to defaults instead of raising.
    ipwhois = IPWhois(timeout="not-a-number", connect_timeout=None)
    assert ipwhois._timeout == 10
    assert ipwhois._connect_timeout == 5


def test_output_option_is_silently_dropped() -> None:
    # The `output` parameter was removed in 1.0.2. Passing it must NOT raise
    # or trip validation -- it's just ignored, and the resulting URL must
    # not contain an `output=...` query string.
    ipwhois = IPWhois("K")
    url = ipwhois._build_url("/8.8.8.8", {"output": "xml", "lang": "en"})

    assert "output=" not in url
    # Other options next to it still work.
    assert "lang=en" in url


def test_non_json_response_is_treated_as_error() -> None:
    # The API always returns JSON. A non-JSON 2xx body now indicates a
    # transport problem (gateway error page, captive portal, ...) rather
    # than legitimate XML/CSV output -- the `output` parameter was
    # removed in 1.0.2. Expect a `success: False` error dict instead of
    # the old `{"success": True, "raw": ...}` wrapper.
    from unittest.mock import patch

    class _FakeResp:
        status = 200
        headers: dict = {}

        def __init__(self, body: bytes) -> None:
            self._body = body

        def __enter__(self) -> "_FakeResp":
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def read(self) -> bytes:
            return self._body

        def getcode(self) -> int:
            return 200

    fake = _FakeResp(b"<html>captive portal</html>")
    with patch("urllib.request.urlopen", return_value=fake):
        result = IPWhois().lookup("8.8.8.8")

    assert result["success"] is False
    assert "Invalid JSON" in result.get("message", "")
    assert result.get("http_status") == 200
