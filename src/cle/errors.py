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


__all__ = [
    "CLEError",
    "DimensionMismatch",
    "NoStrategyConfigured",
    "NotStabilized",
]
