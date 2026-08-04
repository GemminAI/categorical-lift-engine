"""Categorical Lift: the umbrella capability this package is named for.

`CategoricalLiftEngine` (`cle.categorical_lift.engine`) is the composition
root that wires the other eight owned capabilities
(`cle.concept`, `cle.category`, `cle.homotopy`, `cle.quotient`,
`cle.functor`, `cle.natural_transformation`, `cle.crystallization`,
`cle.knowledge_delta`, `cle.commit_candidate`) into one `lift()` call.
"""

from __future__ import annotations

from cle.categorical_lift.engine import CategoricalLiftEngine

__all__ = ["CategoricalLiftEngine"]
