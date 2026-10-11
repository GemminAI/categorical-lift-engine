"""The five CLE metrics: Functorial Invariance, Homotopy Class Determinism,
Entropic Reduction, CET Lineage Integrity, and HEKB Transaction Yield.

Draft v0.1 — not yet reviewed by Tomo. See `docs/METRICS.md` for the
narrative definitions this module implements literally; this module's
docstrings restate only what each function actually computes.

Every function here is pure: given the same arguments, it returns the
same float, with no hidden state and no I/O. Where a metric's real-world
definition needs something CLE itself doesn't own (a live HEKB
connection, a multi-process harness), the function takes that as data the
caller already collected (`HomotopyClassDeterminism` takes already-
serialized diagrams; `hekb_transaction_yield` takes an in-memory sink) —
see each function's docstring for exactly where that boundary is.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Hashable, Mapping
from dataclasses import dataclass, field
from typing import TypeVar

from cle.errors import FunctorialityViolation
from cle.topology.category_theory import FiniteCategory, Functor, Obj
from cle.topology.natural_transformation import NaturalTransformation

_Element = TypeVar("_Element", bound=Hashable)

# --- 1. Functorial Invariance Score -----------------------------------------


def functorial_invariance_score(
    *,
    source: FiniteCategory,
    target: FiniteCategory,
    object_map: Mapping[Obj, Obj],
    morphism_map: Mapping[str, str],
    source_identities: Mapping[Obj, str],
    target_identities: Mapping[Obj, str],
) -> float:
    """Fraction of the two functor axioms a *candidate* mapping satisfies.

    `cle.topology.category_theory.Functor`'s constructor already validates
    every one of these axioms and raises `FunctorialityViolation` on the
    first violation — which makes it unusable for measuring a *partial*
    score (a mapping that fails even one check never becomes a `Functor`
    to measure). This function is CLE's deliberately lenient twin: it
    takes the raw `object_map`/`morphism_map` directly and tallies, over
    every check below, how many hold — a genuine functor scores 1.0 (every
    check it could fail would have raised before `Functor` could even be
    constructed); a candidate mapping that isn't (or isn't yet) a validated
    `Functor` can score anywhere in `[0, 1]`.

    Checked, over every object `source_identities` names an identity for,
    and every composable pair `source.composition` records:

    1. Identity preservation: `F(id_A) == id_{F(A)}`.
    2. Composition preservation: `F(g . f) == F(g) . F(f)`.

    A check that cannot even be evaluated (a referenced object/morphism is
    missing from `object_map`/`morphism_map`, or the mapped morphisms are
    not composable in `target`) counts as *not* satisfied, not skipped.

    Returns `1.0` if there is nothing to check (empty `source_identities`
    and empty `source.composition`) — vacuously true, the same convention
    `FiniteCategory`/`Functor` themselves use for an empty category.
    """
    total = 0
    satisfied = 0

    for obj, identity_name in source_identities.items():
        total += 1
        mapped_obj = object_map.get(obj)
        mapped_identity = morphism_map.get(identity_name)
        expected_identity = (
            target_identities.get(mapped_obj) if mapped_obj is not None else None
        )
        if mapped_identity is not None and mapped_identity == expected_identity:
            satisfied += 1

    for (g_name, f_name), h_name in source.composition.items():
        total += 1
        f_image = morphism_map.get(f_name)
        g_image = morphism_map.get(g_name)
        h_image = morphism_map.get(h_name)
        if f_image is None or g_image is None or h_image is None:
            continue
        composed = target.composition.get((g_image, f_image))
        if composed is not None and composed == h_image:
            satisfied += 1

    return satisfied / total if total else 1.0


# --- 2. Homotopy Class Determinism -------------------------------------------


def homotopy_class_determinism(serialized_results: list[str]) -> float:
    """Fraction of `serialized_results` that are byte-identical to the first.

    The real test (RFC-CLE005-style) this backs computes the *same*
    persistence diagram `N` times, each in a fresh subprocess with a
    different `PYTHONHASHSEED`, serializes each result deterministically
    (floats via `repr`, as this phase's calibration tests require), and
    passes the `N` resulting strings here — this function only measures
    agreement; it does not spawn processes or compute diagrams itself (see
    `tests/test_metrics_calibration.py` for the actual cross-process
    harness).
    """
    if not serialized_results:
        raise ValueError("need at least one result to measure determinism")
    reference = serialized_results[0]
    matches = sum(1 for result in serialized_results if result == reference)
    return matches / len(serialized_results)


# --- 3. Entropic Reduction Delta ---------------------------------------------


def entropic_reduction(
    weights: Mapping[_Element, float], quotient: Mapping[_Element, _Element]
) -> float:
    """`H(X) - H(X/~)` in bits, for the quotient map `quotient: X -> X/~`.

    `weights` is `X`'s empirical distribution (element -> non-negative
    weight; renormalized here, need not already sum to 1). `quotient` maps
    each element of `X` to the class of `X/~` it belongs to; a class's
    weight is the sum of its elements' weights.

    `Delta >= 0` always: merging elements into classes is a coarsening of
    the partition, and entropy can only decrease (or stay equal) under
    coarsening — the grouping property of Shannon entropy, not an
    assumption this function checks. `Delta == 0` exactly when `quotient`
    is injective on `weights`' support (no two elements with positive
    weight actually merge).
    """
    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise ValueError("weights must sum to a positive total")

    element_entropy = -sum(
        (weight / total_weight) * math.log2(weight / total_weight)
        for weight in weights.values()
        if weight > 0
    )

    class_weights: dict[_Element, float] = {}
    for element, weight in weights.items():
        element_class = quotient[element]
        class_weights[element_class] = class_weights.get(element_class, 0.0) + weight

    class_entropy = -sum(
        (weight / total_weight) * math.log2(weight / total_weight)
        for weight in class_weights.values()
        if weight > 0
    )

    return element_entropy - class_entropy


# --- 4. CET Lineage Integrity -------------------------------------------------


def canonical_record_hash(content: str) -> str:
    """The sha256 hex digest `cet_lineage_integrity` expects a record's
    `prev_hash` to match, computed over the *previous* record's `content`.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class TransformationClaim:
    """An unvalidated natural-transformation claim attached to a lineage record.

    Deliberately unvalidated at construction — unlike `NaturalTransformation`
    itself, which raises `FunctorialityViolation` immediately if its square
    doesn't commute. A `LineageRecord` must be constructible even when its
    claim is wrong (that is exactly the "tampered record" case
    `cet_lineage_integrity` needs to be able to detect and score), so the
    validation happens inside `cet_lineage_integrity`, not here.
    """

    source_functor: Functor
    target_functor: Functor
    components: dict[Obj, str]


@dataclass(frozen=True, slots=True)
class LineageRecord:
    """One record in a hash-chained lineage, with an optional transformation claim."""

    content: str
    prev_hash: str | None
    transformation_claim: TransformationClaim | None = None


def cet_lineage_integrity(records: tuple[LineageRecord, ...]) -> float:
    """Fraction of `records` whose hash-chain link AND transformation claim
    (if any) both verify.

    A record is counted as integral when:

    1. Hash chain: its `prev_hash` equals
       `canonical_record_hash(previous_record.content)` — or, for the
       first record, `prev_hash is None`.
    2. Transformation claim: either it has none, or constructing a
       `NaturalTransformation` from it succeeds (its naturality square
       commutes) rather than raising `FunctorialityViolation`.

    `1.0` requires every record in the chain to satisfy both; CLE's own
    tests treat anything less as "this lineage was tampered with"
    (RFC-CLE005's CET requirement). Returns `1.0` for an empty chain
    (vacuously true).
    """
    if not records:
        return 1.0

    integral_count = 0
    previous: LineageRecord | None = None
    for record in records:
        if previous is None:
            hash_ok = record.prev_hash is None
        else:
            hash_ok = record.prev_hash == canonical_record_hash(previous.content)

        claim_ok = True
        if record.transformation_claim is not None:
            claim = record.transformation_claim
            try:
                NaturalTransformation(
                    source_functor=claim.source_functor,
                    target_functor=claim.target_functor,
                    components=claim.components,
                )
            except FunctorialityViolation:
                claim_ok = False

        if hash_ok and claim_ok:
            integral_count += 1
        previous = record

    return integral_count / len(records)


# --- 5. HEKB Transaction Yield ------------------------------------------------


@dataclass(slots=True)
class InMemoryHEKBSink:
    """An in-memory stand-in for HEKB's commit sink, for measuring HEKB
    Transaction Yield inside CLE's own test suite.

    Connecting to the real `hekb-vnext` service is explicitly out of scope
    for this metric (per the brief: CLE's own tests measure this against
    an in-memory sink; the real hekb-vnext connection is separate work) --
    `submit`'s `accept` parameter is supplied directly by the caller
    (standing in for whatever decision the real HEKB sink would have
    made), not computed by this class.
    """

    _committed: list[str] = field(default_factory=list)
    _rejected: list[str] = field(default_factory=list)

    def submit(self, candidate_id: str, *, accept: bool) -> None:
        (self._committed if accept else self._rejected).append(candidate_id)

    @property
    def submitted_count(self) -> int:
        return len(self._committed) + len(self._rejected)

    @property
    def committed_count(self) -> int:
        return len(self._committed)


def hekb_transaction_yield(sink: InMemoryHEKBSink) -> float:
    """`committed / submitted` over everything `sink` has seen so far.

    `1.0` if nothing has been submitted yet (vacuously true — there is no
    rejected candidate to count against the yield).
    """
    if sink.submitted_count == 0:
        return 1.0
    return sink.committed_count / sink.submitted_count


__all__ = [
    "InMemoryHEKBSink",
    "LineageRecord",
    "TransformationClaim",
    "canonical_record_hash",
    "cet_lineage_integrity",
    "entropic_reduction",
    "functorial_invariance_score",
    "hekb_transaction_yield",
    "homotopy_class_determinism",
]
