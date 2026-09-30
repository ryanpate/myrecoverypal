# apps/accounts/safe_fetch.py
"""Fetch a user-supplied URL without letting it reach internal services.

The address is checked on the socket that was actually connected — after DNS
resolution and for every redirect hop — so alternate IP spellings
(2130706433, 0x7f000001), hostnames that resolve to private addresses,
IPv6 forms and redirects to internal hosts are all refused before any
request bytes are sent.
"""
import http.client
import ipaddress
import urllib.request


class NonPublicAddressError(OSError):
    pass


def _require_public_peer(sock):
    peer = sock.getpeername()[0]
    addr = ipaddress.ip_address(peer.split('%')[0])
    if addr.version == 6 and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    if not addr.is_global:
        sock.close()
        raise NonPublicAddressError(f'refusing to fetch from non-public address {peer}')


class _PublicHTTPConnection(http.client.HTTPConnection):
    def connect(self):
        super().connect()
        _require_public_peer(self.sock)


class _PublicHTTPSConnection(http.client.HTTPSConnection):
    def connect(self):
        super().connect()
        _require_public_peer(self.sock)


class _PublicHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(_PublicHTTPConnection, req)


class _PublicHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_PublicHTTPSConnection, req, context=self._context)


_opener = urllib.request.build_opener(_PublicHTTPHandler, _PublicHTTPSHandler)


def open_public_url(request, timeout):
    """Like urllib.request.urlopen, but only ever connects to public addresses."""
    return _opener.open(request, timeout=timeout)
