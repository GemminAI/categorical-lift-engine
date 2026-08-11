"""GroundedState: CLE's Semantic Grounding output. The Meaning-layer
artifact CPS's Selection layer now consumes over HTTP instead of building
locally.

Carries both representations of S/O/K(t):
  - linguistic (fingerprints -- byte-stable sorted tuples, same fix class
    as `cognitive-port-selector`'s determinism fix this session) for
    lexical affinity scoring, the same role CPS's own former
    `SemanticState` fingerprints played;
  - geometric (point clouds, via `cle.grounding.embedding`) for CLE's own
    `CLEEngine.lift`/`.recover`, which only ever accepted point clouds.

Neither representation is derived from the other after construction --
both are built directly from the same S/O/K(t) strings, so they cannot
silently diverge from what was actually said.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from cle.grounding.embedding import Vector, embed_text_as_point_cloud
from cle.grounding.five_w1h import FiveW1H
from cle.grounding.sok import SOK

_TRIGRAM_SIZE = 3


def _char_trigrams(text: str) -> tuple[str, ...]:
    normalized = text.strip().lower()
    if len(normalized) < _TRIGRAM_SIZE:
        return (normalized,) if normalized else ()
    grams = {
        normalized[i : i + _TRIGRAM_SIZE]
        for i in range(len(normalized) - _TRIGRAM_SIZE + 1)
    }
    return tuple(sorted(grams))


class GroundedState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    prompt: str
    goal: str
    five_w1h: FiveW1H
    sok: SOK

    # Lexical (linguistic) representation -- byte-stable sorted tuples.
    fingerprint: tuple[str, ...]
    goal_fingerprint: tuple[str, ...]
    subject_fingerprint: tuple[str, ...]
    observer_fingerprint: tuple[str, ...]
    knowledge_fingerprint: tuple[str, ...]

    # Geometric representation -- point clouds for CLEEngine.
    concept_points: tuple[Vector, ...]
    subject_points: tuple[Vector, ...]
    observer_points: tuple[Vector, ...]
    knowledge_points: tuple[Vector, ...]

    def jaccard_similarity(self, other_text: str) -> float:
        return _jaccard(self.fingerprint, _char_trigrams(other_text))

    def goal_jaccard_similarity(self, other_text: str) -> float:
        return _jaccard(self.goal_fingerprint, _char_trigrams(other_text))

    def subject_jaccard_similarity(self, other_text: str) -> float:
        return _jaccard(self.subject_fingerprint, _char_trigrams(other_text))

    def observer_jaccard_similarity(self, other_text: str) -> float:
        return _jaccard(self.observer_fingerprint, _char_trigrams(other_text))

    def knowledge_jaccard_similarity(self, other_text: str) -> float:
        return _jaccard(self.knowledge_fingerprint, _char_trigrams(other_text))


def _jaccard(a: tuple[str, ...], b: tuple[str, ...]) -> float:
    set_a, set_b = frozenset(a), frozenset(b)
    if not set_a and not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union else 0.0


def build_grounded_state(
    prompt: str,
    goal: str,
    five_w1h: FiveW1H,
    sok: SOK,
    *,
    embedding_dimension: int = 8,
) -> GroundedState:
    combined_text = " ".join(
        [
            prompt,
            goal,
            five_w1h.who.value,
            five_w1h.what.value,
            five_w1h.when.value,
            five_w1h.where.value,
            five_w1h.why.value,
            five_w1h.how.value,
        ]
    )
    return GroundedState(
        prompt=prompt,
        goal=goal,
        five_w1h=five_w1h,
        sok=sok,
        fingerprint=_char_trigrams(combined_text),
        goal_fingerprint=_char_trigrams(goal),
        subject_fingerprint=_char_trigrams(sok.subject),
        observer_fingerprint=_char_trigrams(sok.observer),
        knowledge_fingerprint=_char_trigrams(sok.knowledge_reference),
        concept_points=embed_text_as_point_cloud(
            combined_text, dimension=embedding_dimension
        ),
        subject_points=embed_text_as_point_cloud(
            sok.subject, dimension=embedding_dimension
        ),
        observer_points=embed_text_as_point_cloud(
            sok.observer, dimension=embedding_dimension
        ),
        knowledge_points=embed_text_as_point_cloud(
            sok.knowledge_reference, dimension=embedding_dimension
        ),
    )


__all__ = ["GroundedState", "build_grounded_state"]
