"""Bridges linguistic text (a Prompt, or one S/O/K(t) axis) to the numeric
point cloud `cle.runtime.engine.CLEEngine` actually consumes.

Before this module, CLE's `subject_context`/`observer_context`/
`human_knowledge_context` had no producer anywhere in this codebase other
than test fixtures handing it synthetic coordinates directly -- there was
no path from *text* to a point cloud. `cle.grounding.sok`/`five_w1h`
produce linguistic content (strings); `cle.runtime.engine` requires
`Vector = tuple[float, ...]` point clouds. This module is that path, and
without it, feeding real S/O/K(t) strings into `CLEEngine.lift`/`.recover`
would still be structurally impossible even after Grounding exists.

Design, stated plainly rather than left implicit:

- One point per unique character trigram in the text (not one point for
  the whole string) -- a single point produces a topologically trivial
  category under `_category_from_point_cloud`'s Vietoris-Rips construction
  (one object, one identity morphism, zero edges), which would make
  `pullback`/`pushout`/Betti numbers constant regardless of content. Many
  points, one per trigram, gives the simplicial complex real structure to
  be sensitive to.
- Each trigram maps to a fixed-dimension coordinate via SHA-256 (not
  Python's `hash()`, which is randomized per-process by `PYTHONHASHSEED`
  unless the interpreter disables it -- the exact defect class fixed in
  `cognitive-port-selector` this session, not reintroduced here).
- No learned weights, no external model call: this is a disclosed,
  reproducible hash-embedding (the same technique class CPS's/nvs-kernel's
  existing char-trigram lexical machinery already uses, extended from a
  string-similarity score to a numeric coordinate), not a semantic
  embedding model. Two different strings sharing no trigrams produce
  disjoint point clouds; two similar strings produce overlapping ones.
  This is a real, causal, reproducible mapping -- not a claim that it is
  linguistically sophisticated.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

Vector = tuple[float, ...]
_TRIGRAM_SIZE = 3
_DEFAULT_DIMENSION = 8


def char_trigrams(text: str) -> tuple[str, ...]:
    """Sorted, deduplicated character trigrams -- stable iteration order
    regardless of set/dict hash-seed randomization (same fix class as
    `cognitive-port-selector`'s `semantic_state.py` this session)."""
    normalized = text.strip().lower()
    if len(normalized) < _TRIGRAM_SIZE:
        return (normalized,) if normalized else ()
    grams = {
        normalized[i : i + _TRIGRAM_SIZE]
        for i in range(len(normalized) - _TRIGRAM_SIZE + 1)
    }
    return tuple(sorted(grams))


def _trigram_vector(trigram: str, dimension: int) -> Vector:
    """SHA-256(trigram) -> `dimension` floats in [-1.0, 1.0], L2-normalized.

    Deterministic across processes/interpreters (unlike `hash()`); two
    equal trigrams always produce the identical vector; two different
    trigrams produce (with overwhelming probability) different vectors,
    uniformly distributed on the unit sphere in R^dimension.
    """
    digest = hashlib.sha256(trigram.encode("utf-8")).digest()
    raw = tuple(
        (digest[i % len(digest)] / 127.5) - 1.0  # byte in [0,255] -> float in [-1, ~1]
        for i in range(dimension)
    )
    # norm == 0.0 is unreachable: a component is exactly 0.0 only if
    # byte == 127.5, impossible for an integer byte in [0, 255], so at
    # least one component is always nonzero.
    norm = sum(component**2 for component in raw) ** 0.5
    return tuple(component / norm for component in raw)


def embed_text_as_point_cloud(
    text: str, *, dimension: int = _DEFAULT_DIMENSION
) -> tuple[Vector, ...]:
    """One `Vector` per unique character trigram in `text`, sorted for
    determinism. Empty/whitespace-only text produces a single canonical
    origin point (`(0.0,) * dimension`) rather than an empty tuple, so
    downstream `VietorisRipsComplex` construction always has >=1 point to
    work with -- this is what makes "empty S/O/K(t)" a real, distinct,
    reproducible point in the space (the canonical origin), not an error.
    """
    grams = char_trigrams(text)
    if not grams:
        return ((0.0,) * dimension,)
    return tuple(_trigram_vector(gram, dimension) for gram in grams)


@dataclass(frozen=True, slots=True)
class _Point:
    """Satisfies `cle.abi.inputs.MeaningStateLike`'s `.theta` duck-type
    (only `.theta` is actually read by
    `cle.runtime.engine._coordinates_of`)."""

    theta: Vector


@dataclass(frozen=True, slots=True)
class PointCloud:
    """Satisfies `StabilizedTrajectoryLike`'s `.states` duck-type (only
    `.states[i].theta` is actually read) -- the minimal shape
    `CLEEngine.lift`/`.recover` need, built directly from
    `embed_text_as_point_cloud`'s output rather than requiring a real
    `StabilizedTrajectory` from `meaning-space-runtime`. Grounding is a
    *new* upstream producer for CLE's existing engine, not a caller of
    MSR's."""

    states: tuple[_Point, ...]

    @classmethod
    def from_text(cls, text: str, *, dimension: int = _DEFAULT_DIMENSION) -> PointCloud:
        return cls(
            states=tuple(
                _Point(theta=v)
                for v in embed_text_as_point_cloud(text, dimension=dimension)
            )
        )

    @classmethod
    def from_vectors(cls, vectors: tuple[Vector, ...]) -> PointCloud:
        return cls(states=tuple(_Point(theta=v) for v in vectors))


__all__ = ["PointCloud", "Vector", "char_trigrams", "embed_text_as_point_cloud"]
