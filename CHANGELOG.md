# Changelog

All notable changes to `ipwhois-python` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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