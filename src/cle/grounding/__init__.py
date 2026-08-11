"""Semantic Grounding: CLE's Meaning-layer entry point.

Turns a Prompt/Goal into 5W1H + S/O/K(t) + a `GroundedState` whose
subject/observer/knowledge axes are real numeric point clouds, consumable
directly by `cle.runtime.engine.CLEEngine.lift`/`.recover` -- the existing,
previously-disconnected categorical machinery this package's `service.ground`
now actually drives.

Relocated from `cognitive-port-selector`'s `cps.grounding` (2026-08-12
CLE-rebuild directive): CPS is Selection-only from this point forward: it
consumes CLE's `/ground` output rather than constructing S/O/K(t) itself.
`five_w1h.py`/`sok.py` are the same logic, moved rather than duplicated.
"""

from __future__ import annotations

from cle.grounding.embedding import PointCloud, embed_text_as_point_cloud
from cle.grounding.five_w1h import (
    FiveW1H,
    FiveW1HField,
    FiveW1HOverrides,
    Source,
    extract_five_w1h,
)
from cle.grounding.semantic_state import GroundedState, build_grounded_state
from cle.grounding.service import GroundingResult, ground
from cle.grounding.sok import SOK, SOKOverrides, build_sok, detect_shift

__all__ = [
    "SOK",
    "FiveW1H",
    "FiveW1HField",
    "FiveW1HOverrides",
    "GroundedState",
    "GroundingResult",
    "PointCloud",
    "SOKOverrides",
    "Source",
    "build_grounded_state",
    "build_sok",
    "detect_shift",
    "embed_text_as_point_cloud",
    "extract_five_w1h",
    "ground",
]
