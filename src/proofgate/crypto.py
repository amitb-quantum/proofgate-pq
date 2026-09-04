"""Provider-only signatures; suite composition is application protocol, not a primitive."""

import base64
import binascii
from typing import Any

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives.asymmetric import ed25519, mldsa

from .canonical import canonical
from .errors import GateError, require

SUITES: dict[str, tuple[str, ...]] = {
    "ed25519-v1": ("ed25519",),
    "mldsa65-v1": ("ml-dsa-65",),
    "ed25519-mldsa65-v1": ("ed25519", "ml-dsa-65"),
}
PRIVATE: dict[str, Any] = {
    "ed25519": ed25519.Ed25519PrivateKey,
    "ml-dsa-65": mldsa.MLDSA65PrivateKey,
}
PUBLIC: dict[str, Any] = {
    "ed25519": ed25519.Ed25519PublicKey,
    "ml-dsa-65": mldsa.MLDSA65PublicKey,
}
SIZES = {"ed25519": (32, 64), "ml-dsa-65": (1952, 3309)}


def components(suite: str) -> tuple[str, ...]:
    require(suite in SUITES, "SUITE_UNSUPPORTED")
    return SUITES[suite]


def encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def unbase64(value: str) -> bytes:
    try:
        result = base64.b64decode(value, validate=True)
        require(encode(result) == value, "BASE64_INVALID")
        return result
    except (binascii.Error, ValueError) as exc:
        raise GateError("BASE64_INVALID") from exc


def generate(suite: str) -> tuple[dict[str, str], dict[str, str]]:
    private, public = {}, {}
    try:
        for algorithm in components(suite):
            key = PRIVATE[algorithm].generate()
            private[algorithm] = encode(key.private_bytes_raw())
            public[algorithm] = encode(key.public_key().public_bytes_raw())
    except UnsupportedAlgorithm as exc:
        raise GateError("PROVIDER_UNAVAILABLE") from exc
    return private, public


def message(domain: str, suite: str, identity: str, body: Any) -> bytes:
    require(domain in {"intent", "attestation", "result", "benchmark"}, "DOMAIN_INVALID")
    return (
        b"ProofGate-PQ/v1/"
        + domain.encode()
        + b"\0"
        + canonical(
            {
                "suite": suite,
                "signer": identity,
                "body": body.model_dump(mode="json") if hasattr(body, "model_dump") else body,
            }
        )
    )


def sign(suite: str, private: dict[str, str], data: bytes) -> dict[str, str]:
    require(set(private) == set(components(suite)), "KEY_COMPONENTS")
    signatures = {}
    try:
        for algorithm in components(suite):
            raw = unbase64(private[algorithm])
            key = (
                PRIVATE[algorithm].from_seed_bytes(raw)
                if algorithm == "ml-dsa-65"
                else PRIVATE[algorithm].from_private_bytes(raw)
            )
            signatures[algorithm] = encode(key.sign(data))
    except UnsupportedAlgorithm as exc:
        raise GateError("PROVIDER_UNAVAILABLE") from exc
    except ValueError as exc:
        raise GateError("KEY_INVALID") from exc
    return signatures


def check_public(suite: str, public: dict[str, str]) -> None:
    require(set(public) == set(components(suite)), "KEY_COMPONENTS")
    try:
        for algorithm in components(suite):
            PUBLIC[algorithm].from_public_bytes(unbase64(public[algorithm]))
    except UnsupportedAlgorithm as exc:
        raise GateError("PROVIDER_UNAVAILABLE") from exc
    except ValueError as exc:
        raise GateError("KEY_INVALID") from exc


def verify(suite: str, public: dict[str, str], signatures: dict[str, str], data: bytes) -> None:
    required = set(components(suite))
    require(set(signatures) == required, "SIGNATURE_COMPONENTS")
    require(set(public) == required, "KEY_COMPONENTS")
    try:
        for algorithm in components(suite):
            signature = unbase64(signatures[algorithm])
            require(len(signature) == SIZES[algorithm][1], "SIGNATURE_INVALID")
            key = PUBLIC[algorithm].from_public_bytes(unbase64(public[algorithm]))
            key.verify(signature, data)
    except InvalidSignature as exc:
        raise GateError("SIGNATURE_INVALID") from exc
    except UnsupportedAlgorithm as exc:
        raise GateError("PROVIDER_UNAVAILABLE") from exc
    except ValueError as exc:
        raise GateError("KEY_INVALID") from exc
