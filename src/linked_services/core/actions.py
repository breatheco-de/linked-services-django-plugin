import secrets

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

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
