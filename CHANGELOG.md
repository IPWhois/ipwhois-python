# Changelog

All notable changes to `ipwhois-python` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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