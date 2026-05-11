# Changelog

All notable changes to `ipwhois-python` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.1] - 2026-05-11

### Changed

- README "Error response fields" table now lists `success` explicitly as the
  first row — it is always present on error responses (set to `false`) and
  is the canonical field to branch on. Previously the table started with
  `message`, even though every example in the README checks `info["success"]`.
- README "Response shape" example for errors updated to show an HTTP 429
  scenario (rate limit) instead of an HTTP 400 (invalid IP). The new example
  illustrates `retry_after` as a real present field rather than a commented-
  out hint, which better reflects how callers actually consume the response
  on the free plan.

## [1.2.0] - 2026-05-10

### Added

- Every error response now carries an `error_type` field, including errors
  returned by the API. The new value `'api'` joins the existing `'network'`
  and `'invalid_argument'` codes, so callers can branch on the category of
  any failure with a single `info["error_type"]` check — no need to combine
  `success` with `http_status` to distinguish API vs. non-API errors.
  Applies to HTTP 4xx / 5xx responses, malformed JSON bodies, and HTTP 2xx
  responses where the API itself sets `success: false` (e.g. "Invalid IP
  address", "Reserved range").

### Changed

- `retry_after` is now only attached to HTTP 429 responses on the **free
  plan** (`ipwho.is`). The paid endpoint (`ipwhois.pro`) does not send a
  `Retry-After` header, so reading it on paid plans is now skipped and the
  field will not appear there. Behaviour on the free plan is unchanged.
- README "Setting defaults once" section now shows the Free and Paid plans
  as two separate code blocks, matching the layout used in "Quick start"
  and "HTTPS encryption". The setters work identically on both plans, so
  the lookup-override snippet is shared underneath.
- README "Error response fields" table now lists `message` explicitly (it
  has always been present on every error response) and the `error_type`
  row covers the new `'api'` value as well.
- The `_request()` HTTP-error code path was lightly refactored so the
  `Retry-After` header is parsed in one place instead of two (one for the
  dict branch and one for the list branch). No behaviour change beyond the
  free-plan gating noted above.

## [1.0.2] - 2026-05-10

### Removed

- **The `output` option has been removed.** The library only ever processed
  JSON responses meaningfully, so `output="xml"` and `output="csv"` were a
  thin pass-through that returned the raw payload as a string. The option
  has been dropped from `lookup()`, `bulk_lookup()`, and the constructor's
  keyword arguments; the `IPWhois.SUPPORTED_OUTPUTS` constant is gone.
  Passing `output=...` will silently no-op.
- The 2xx + non-JSON `{"success": True, "raw": ...}` fallback in the
  response handler (which only existed to support the removed `output`
  parameter) is gone. The API always returns JSON, so any non-JSON 2xx
  body is now treated as a transport error and returned as a
  `success: False` dict.

### Changed

- `set_fields()` docstring now mentions that `"success"` should be included
  in the field whitelist if you rely on `info["success"]` for error
  checking — when `fields` is set, the API only returns the fields you list.
- README "Setting defaults once" section rewritten for clarity: the two
  ways of passing options (per call vs. as defaults), the available
  setters, and the `success`-in-`fields` gotcha are now spelled out
  explicitly. The free/paid example pair was collapsed into a single
  example, since the setters work identically on both plans.
- All examples that filter fields (`README.md`, `examples/basic.py`,
  `examples/defaults.py`) now include `"success"` in the field list.

### Migration

If your code passes `output="json"` you can simply remove it — the library
always returns the decoded JSON anyway. If you were relying on
`output="xml"` or `output="csv"` to get the raw payload, that use case is
no longer supported; call the API directly with `urllib` for those formats.

```python
# Before (1.0.1):
info = ipwhois.lookup("8.8.8.8", output="json", fields=["country", "city"])

# After (1.0.2):
info = ipwhois.lookup("8.8.8.8", fields=["success", "country", "city"])
```

## [1.0.1] - 2026-05-09

### Changed

- **Renamed the main class `Client` to `IPWhois`** for consistency with the
  package and brand. The recommended import is now
  `from ipwhois import IPWhois`. The source module moved from
  `src/ipwhois/client.py` to `src/ipwhois/ipwhois.py`, and the test module
  from `tests/test_client.py` to `tests/test_ipwhois.py`. Public behaviour,
  method signatures, constructor arguments, and return shapes are all
  unchanged.

### Migration

```python
# Before (1.0.0):
from ipwhois import Client
client = Client("YOUR_API_KEY")
info   = client.lookup("8.8.8.8")

# After (1.0.1+):
from ipwhois import IPWhois
ipwhois = IPWhois("YOUR_API_KEY")
info    = ipwhois.lookup("8.8.8.8")
```

The variable name (`client`, `ipwhois`, anything else) is up to you; only
the class identifier changed.

## [1.0.0] - 2026-05-08

### Added

- Initial release. 