"""CLE error taxonomy.

Every error raised across a CLE boundary derives from :class:`CLEError`, so a
host process can distinguish "the input was rejected" from "no strategy was
configured for this stage" without catching bare exceptions. Mirrors the
convention `msr.errors` establishes in `meaning-space-runtime`.
"""

from __future__ import annotations


class CLEError(Exception):
    """Base class for every error raised by the Categorical Lift Engine."""


class NotStabilized(CLEError):
    """The input was not a stabilized artifact.

    CLE accepts only stabilized runtime artifacts (a `StabilizedTrajectory`
    with at least one state and a positive dwell). A trajectory that never
    latched is Meaning Space Runtime's concern, not CLE's — CLE does not
    perform semantic measurement or evolve runtime state, so it has no basis
    for interpreting an unstabilized trajectory.
    """


class DimensionMismatch(CLEError):
    """A vector or matrix on the input side did not match the declared dimension."""


class NoStrategyConfigured(CLEError):
    """A `CategoricalLiftEngine` stage was invoked with no strategy injected.

    CLE's engine composes `Protocol`-typed stage strategies (concept
    discovery, category construction, homotopy analysis, quotient
    construction, functor construction, natural transformation analysis,
    crystallization, knowledge delta generation, commit-candidate building).
    None of them has a built-in default: this repository is deliberately a
    skeleton, not a categorical-theory implementation, so a stage that is
    exercised without a configured strategy fails loudly instead of
    fabricating a result.
    """


class InvalidTrajectory(CLEError):
    """A trajectory's own fields disagree in a way no strategy can resolve.

    Added post-Phase-1 architectural review: `StabilizedTrajectoryLike.is_novel`
    and `.basin_id` are independent properties on the real Protocol — nothing
    guarantees `basin_id is not None` whenever `is_novel` is `False`, that
    relationship only held in the test fixture. Rather than hashing `None`
    into a fabricated concept id when a reinforcing trajectory has no
    `basin_id` and no `hekb_context` match to fall back on,
    `FunctorialConceptLift` raises this instead — the same "fail loudly, not
    fabricate" convention as `NotStabilized`/`NoStrategyConfigured`.
    """


class FunctorialityViolation(CLEError):
    """No structure-preserving mapping exists between two categorical structures.

    Added for RFC-CLE001 Phase 1 (Functorial Lift Engine): RFC-CLE002 §5
    names this failure mode `QuarantineReason.FUNCTORIALITY_VIOLATION` and
    routes it through a `quarantine_stage` field this repository's frozen
    ABI does not have (see `docs/RFC_ALIGNMENT.md`). Rather than adding that
    field pre-emptively, this repository keeps its existing exception-based
    failure convention (`NotStabilized`, `NoStrategyConfigured`): a
    `FunctorConstructor` implementation that cannot derive a functor between
    the two categories it was given fails loudly here instead of fabricating
    one.
    """


class NonFiniteValue(CLEError):
    """A coordinate or scalar was NaN or infinite where a finite value is required.

    Added for RFC-CLE005 §4.1 (Phase 5, Validation): NaN/Inf coordinate
    injection is named there as its own explicit fault-injection category.
    Discovered empirically, not assumed: before this was added, a NaN
    centroid passed through `FunctorialConceptLift`/`EpsilonGraphBettiAnalyzer`
    completely silently — no exception, no wrong-but-detectable answer.
    Silent propagation is actively worse than a wrong answer here, since
    `float('nan') <= eps` and `float('nan') == float('nan')` are both
    `False` in Python: a NaN coordinate doesn't just corrupt a result, it
    makes every subsequent proximity/equality check against it silently
    behave as "infinitely far" without ever raising.
    """


__all__ = [
    "CLEError",
    "DimensionMismatch",
    "FunctorialityViolation",
    "InvalidTrajectory",
    "NoStrategyConfigured",
    "NonFiniteValue",
    "NotStabilized",
]
