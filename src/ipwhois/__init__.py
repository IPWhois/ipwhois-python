"""Official Python client for the ipwhois.io IP Geolocation API.

See :class:`ipwhois.Client` for usage. The library never raises -- every
failure comes back inside the response dict with ``success`` set to ``False``
and a ``message``.
"""

from .client import Client

__all__ = ["Client", "__version__"]
__version__ = Client.VERSION
