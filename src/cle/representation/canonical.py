"""Canonical JSON and SHA-256 content hashes (CLE v0.3 section 2.1).

Canonical form: keys ascending, separators ``(",", ":")``, ``ensure_ascii=False``,
UTF-8. Floats are refused outright (D-72): a value that is not an int, str,
bool, None, list/tuple or str-keyed dict cannot be hashed.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _reject_floats(value: Any, path: str = "$") -> None:
    if isinstance(value, float):
        raise TypeError(f"floats are not allowed in canonical JSON (at {path})")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"non-string key {key!r} at {path}")
            _reject_floats(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_floats(item, f"{path}[{index}]")
    elif value is not None and not isinstance(value, (str, int)):
        raise TypeError(f"unsupported type {type(value).__name__} at {path}")


def canonical_json(value: Any) -> str:
    _reject_floats(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


__all__ = ["canonical_json", "sha256_hex"]
