"""PGJ-1 canonicalization. Narrow by design; this is not generic JSON/JCS."""

import hashlib
import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from .errors import GateError, require

MAX_BYTES = 1_048_576
T = TypeVar("T", bound=BaseModel)


def _check(value: Any, depth: int = 0) -> None:
    require(depth <= 32, "CANONICAL_DEPTH")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        require(abs(value) <= 2**53 - 1, "CANONICAL_INTEGER")
    elif type(value) is str:
        require(all(32 <= ord(c) <= 126 for c in value), "CANONICAL_STRING")
    elif type(value) is list:
        for item in value:
            _check(item, depth + 1)
    elif type(value) is dict:
        for key, item in value.items():
            require(type(key) is str, "CANONICAL_KEY")
            _check(key, depth + 1)
            _check(item, depth + 1)
    else:
        raise GateError("CANONICAL_TYPE")


def canonical(value: Any) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    _check(value)
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    require(len(encoded) <= MAX_BYTES, "DOCUMENT_TOO_LARGE")
    return encoded


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _integer(value: str) -> int:
    require(value != "-0", "CANONICAL_INTEGER")
    return int(value)


def _reject_number(value: str) -> Any:
    raise GateError("CANONICAL_NUMBER")


def decode(data: bytes) -> Any:
    require(len(data) <= MAX_BYTES, "DOCUMENT_TOO_LARGE")
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_int=_integer,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
        _check(value)
        return value
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise GateError("MALFORMED_JSON") from exc


def parse(model: type[T], data: bytes) -> T:
    try:
        return model.model_validate(decode(data))
    except ValidationError as exc:
        raise GateError("SCHEMA_INVALID") from exc


def digest(domain: str, value: Any) -> str:
    return hashlib.sha384(
        b"ProofGate-PQ/v1/" + domain.encode("ascii") + b"\0" + canonical(value)
    ).hexdigest()


def read(path: Path) -> bytes:
    with path.open("rb") as stream:
        value = stream.read(MAX_BYTES + 1)
    require(len(value) <= MAX_BYTES, "DOCUMENT_TOO_LARGE")
    return value


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value) + b"\n")
