"""Official Python client for the ipwhois.io IP Geolocation API.

See :class:`ipwhois.IPWhois` for usage. The library never raises -- every
failure comes back inside the response dict with ``success`` set to ``False``
and a ``message``.
"""

from .ipwhois import IPWhois

__all__ = ["IPWhois", "__version__"]
__version__ = IPWhois.VERSION
