"""CLE as an independent Cognitive Service, over HTTP.

Phase 1: a thin FastAPI controller over `cle.runtime`, `cle.topology`, and
`cle.compression`. No categorical-theory algorithm lives in this package —
every request is deserialized into the shape the reused domain function
already expects, delegated to it unchanged, and the result serialized back.
See `docs/ARCHITECTURE.md` for what each stage reuses.
"""

from __future__ import annotations
