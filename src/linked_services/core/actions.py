import secrets
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)


def set_query_parameter(url: str, **kwargs: str):
    """Given a URL, set or replace a query parameter and return the
    modified URL.

    >>> set_query_parameter('http://example.com?foo=bar&biz=baz', foo='stuff')
    'http://example.com?foo=stuff&biz=baz'

    """
    scheme, netloc, path, query_string, fragment = urlsplit(url)
    query_params = parse_qs(query_string)

    for param_name, param_value in kwargs.items():
        if param_value is None:
            param_value = ""

        query_params[param_name] = [param_value]

    new_query_string = urlencode(query_params, doseq=True)

    return urlunsplit((scheme, netloc, path, new_query_string, fragment))


JWT_LIFETIME = 10


def generate_auth_keys(algorithm) -> tuple[bytes, bytes]:
    public_key = None
    key = Ed25519PrivateKey.generate()

    if algorithm == "HMAC_SHA256" or algorithm == "HMAC_SHA512":
        private_key = secrets.token_hex(64)

    elif algorithm == "ED25519":
        private_key = key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption(),
        ).hex()

        public_key = (
            key.public_key().public_bytes(encoding=Encoding.PEM, format=PublicFormat.SubjectPublicKeyInfo).hex()
        )

    return public_key, private_key
