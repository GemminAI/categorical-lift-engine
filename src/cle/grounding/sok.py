"""S / O / K(t) triangulation.

S = Subject   (whose story/position/target)
O = Observer  (whose observation frame)
K(t) = Knowledge Reference (which knowledge system/timepoint is the basis)

Relocated verbatim from `cognitive-port-selector`'s `cps.grounding.sok`
(2026-08-12 CLE-rebuild directive). Structurally related to (but not
derived from) `nvs-kernel`'s `ThreeViewTrajectoryRecovery`
(Subject/Observer/Human-Knowledge anchors) and this repo's own
`three_view_pullback` -- both read-only inspiration for the naming, not
imported. This module produces the *linguistic* S/O/K(t) (three strings,
with provenance); `cle.grounding.embedding` bridges each string to the
*geometric* point cloud `cle.runtime.engine.CLEEngine` actually consumes.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from cle.grounding.five_w1h import FiveW1H, Source

_DEFAULT_OBSERVER = "CLE"


class SOKOverrides(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    subject: str | None = None
    observer: str | None = None
    knowledge_reference: str | None = None


class SOK(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    subject: str
    subject_source: Source
    observer: str
    observer_source: Source
    knowledge_reference: str
    knowledge_reference_source: Source


def build_sok(
    five_w1h: FiveW1H,
    overrides: SOKOverrides | None = None,
    default_knowledge_reference: str = "unspecified",
) -> SOK:
    overrides = overrides or SOKOverrides()

    subject: str
    subject_source: Source
    observer: str
    observer_source: Source
    knowledge_reference: str
    knowledge_reference_source: Source

    if overrides.subject is not None and overrides.subject.strip():
        subject, subject_source = overrides.subject.strip(), "explicit"
    elif five_w1h.who.source != "unspecified":
        subject, subject_source = five_w1h.who.value, "derived"
    else:
        subject, subject_source = "unspecified", "unspecified"

    if overrides.observer is not None and overrides.observer.strip():
        observer, observer_source = overrides.observer.strip(), "explicit"
    else:
        observer, observer_source = _DEFAULT_OBSERVER, "derived"

    if (
        overrides.knowledge_reference is not None
        and overrides.knowledge_reference.strip()
    ):
        knowledge_reference, knowledge_reference_source = (
            overrides.knowledge_reference.strip(),
            "explicit",
        )
    elif default_knowledge_reference != "unspecified":
        knowledge_reference, knowledge_reference_source = (
            default_knowledge_reference,
            "derived",
        )
    else:
        knowledge_reference, knowledge_reference_source = "unspecified", "unspecified"

    return SOK(
        subject=subject,
        subject_source=subject_source,
        observer=observer,
        observer_source=observer_source,
        knowledge_reference=knowledge_reference,
        knowledge_reference_source=knowledge_reference_source,
    )


def detect_shift(before: SOK, after: SOK) -> tuple[str, ...]:
    """Returns which of S/O/K(t) changed between two states -- e.g. to
    distinguish "S is the same, O changed" from "O is the same, K(t)
    changed"."""

    shifted = []
    if before.subject != after.subject:
        shifted.append("subject")
    if before.observer != after.observer:
        shifted.append("observer")
    if before.knowledge_reference != after.knowledge_reference:
        shifted.append("knowledge_reference")
    return tuple(shifted)


__all__ = ["SOK", "SOKOverrides", "build_sok", "detect_shift"]
