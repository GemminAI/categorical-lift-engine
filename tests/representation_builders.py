"""Small builders shared by the representation tests and the golden generator."""

from __future__ import annotations

from typing import Any

from cle.representation import (
    AbandonedBranch,
    Composition,
    Invertibility,
    PropertyVocabulary,
    Ref,
    RepresentationHistory,
    RepresentationMorphism,
    RepresentationState,
    Span,
)

PROPS = ("shape", "count")
INFO = ("order",)
VOCAB_REF = Ref("hext", "vocab-v1", seal_status="SEAL_OK")
RULE_REF = Ref("hext", "rule-v1", seal_status="SEAL_OK")


def vocab() -> PropertyVocabulary:
    return PropertyVocabulary("vocab", "1", "task", PROPS, INFO, VOCAB_REF)


def state(sid: str, span: Span | None = None, **kw: Any) -> RepresentationState:
    return RepresentationState(sid, "h", "kind", span=span, **kw)


def ident(sid: str, **kw: Any) -> RepresentationMorphism:
    return RepresentationMorphism(
        f"i{sid.lower()}",
        sid,
        sid,
        role="identity",
        preserved=PROPS,
        carry={p: p for p in PROPS},
        **kw,
    )


def mor(mid: str, a: str, b: str, **kw: Any) -> RepresentationMorphism:
    kw.setdefault("rule_ref", RULE_REF)
    kw.setdefault("preserved", PROPS)
    kw.setdefault("carry", {p: p for p in PROPS})
    return RepresentationMorphism(mid, a, b, **kw)


def history(
    states: list[RepresentationState],
    morphisms: list[RepresentationMorphism],
    compositions: list[Composition] | None = None,
    *,
    identities: bool = True,
    branches: list[AbandonedBranch] | None = None,
    prev: str | None = None,
) -> RepresentationHistory:
    extra = [ident(s.state_id) for s in states] if identities else []
    return RepresentationHistory(
        history_id="h",
        task_ref="task",
        vocabulary_ref=VOCAB_REF,
        states=tuple(states),
        morphisms=tuple(extra + morphisms),
        compositions=tuple(compositions or ()),
        abandoned_branches=tuple(branches or ()),
        prev_history_hash=prev,
    ).seal()


def chain(**overrides: Any) -> RepresentationHistory:
    """A -f-> B -g-> C and a directly recorded k: A -> C with (f, g) -> k."""
    parts: dict[str, Any] = {
        "states": [state("A"), state("B"), state("C")],
        "morphisms": [
            mor("f", "A", "B"),
            mor("g", "B", "C"),
            mor("k", "A", "C"),
        ],
        "compositions": [Composition("f", "g", "k")],
    }
    parts.update(overrides)
    return history(**parts)


def invertible_pair(**overrides: Any) -> RepresentationHistory:
    """f: A -> B claimed invertible with inverse r, both sides in the table."""
    parts: dict[str, Any] = {
        "states": [state("A"), state("B")],
        "morphisms": [
            mor("f", "A", "B", invertibility=Invertibility("invertible", "r")),
            mor("r", "B", "A", role="inverse_claim"),
        ],
        "compositions": [Composition("f", "r", "ia"), Composition("r", "f", "ib")],
    }
    parts.update(overrides)
    return history(**parts)
