"""RFC-CLE005 §4: fault-injection / quarantine tests.

This repository's "quarantine" is exception-based (`CLEError` subclasses),
not a `quarantine_stage` field — see `docs/RFC_ALIGNMENT.md`'s Phase 1
addendum for why that field was never added to the ABI. These tests verify
the actual, adapted claim: NaN/Inf coordinate injection must raise
`NonFiniteValue`, never silently propagate and never crash with an
unrelated, unhandled exception.

Before `NonFiniteValue`/`assert_finite` existed (Phase 5 validation work),
this was verified empirically to be false: a NaN centroid produced a
`Concept`/Betti result with no exception anywhere. These tests lock in the
fix and use Hypothesis to fuzz beyond the hand-picked cases.
"""

from __future__ import annotations

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cle.abi.inputs import MeaningStateLike
from cle.concept import FunctorialConceptLift
from cle.errors import NonFiniteValue
from cle.geometry import assert_finite
from cle.homotopy import EpsilonGraphBettiAnalyzer


@st.composite
def _vectors_with_one_non_finite_component(draw: st.DrawFn) -> tuple[float, ...]:
    dim = draw(st.integers(min_value=1, max_value=5))
    non_finite = draw(st.sampled_from([math.nan, math.inf, -math.inf]))
    bad_index = draw(st.integers(min_value=0, max_value=dim - 1))
    values = [
        draw(st.floats(allow_nan=False, allow_infinity=False, width=32))
        for _ in range(dim)
    ]
    values[bad_index] = non_finite
    return tuple(values)


@given(vector=_vectors_with_one_non_finite_component())
def test_assert_finite_rejects_any_nan_or_inf_component(
    vector: tuple[float, ...],
) -> None:
    with pytest.raises(NonFiniteValue):
        assert_finite(vector)


@given(
    vector=st.lists(
        st.floats(allow_nan=False, allow_infinity=False, width=32),
        min_size=1,
        max_size=5,
    ).map(tuple)
)
def test_assert_finite_accepts_any_all_finite_vector(vector: tuple[float, ...]) -> None:
    assert_finite(vector)  # must not raise


class _FakeTrajectory:
    trajectory_id = "traj-fuzz"
    frame_id = "F"
    basin_id = None
    states: tuple[MeaningStateLike, ...] = ()
    covariance = ((1.0, 0.0), (0.0, 1.0))
    dwell_steps = 1
    dwell_seconds = 0.1
    provenance: tuple[str, ...] = ()
    is_novel = True

    def __init__(self, centroid: tuple[float, float]) -> None:
        self.centroid = centroid


@pytest.mark.parametrize("bad_value", [math.nan, math.inf, -math.inf])
def test_nan_or_inf_centroid_is_quarantined_not_silently_propagated(
    bad_value: float,
) -> None:
    lift = FunctorialConceptLift()
    trajectory = _FakeTrajectory(centroid=(bad_value, 1.0))

    with pytest.raises(NonFiniteValue):
        lift.discover(trajectory, hekb_context=None)


def test_nan_coordinate_in_betti_computation_is_quarantined() -> None:
    analyzer = EpsilonGraphBettiAnalyzer()

    with pytest.raises(NonFiniteValue):
        analyzer.compute_betti_numbers(
            ((0.0, 0.0), (math.nan, 0.0), (1.0, 0.0)), eps=0.5
        )


def test_inf_coordinate_in_betti_computation_is_quarantined() -> None:
    analyzer = EpsilonGraphBettiAnalyzer()

    with pytest.raises(NonFiniteValue):
        analyzer.compute_betti_numbers(((0.0, 0.0), (math.inf, 0.0)), eps=0.5)


@given(
    coordinates=st.lists(
        st.tuples(
            st.floats(allow_nan=False, allow_infinity=False, width=32),
            st.floats(allow_nan=False, allow_infinity=False, width=32),
        ),
        min_size=1,
        max_size=8,
    )
)
def test_all_finite_coordinates_never_raise_non_finite_value(
    coordinates: list[tuple[float, float]],
) -> None:
    analyzer = EpsilonGraphBettiAnalyzer()

    # Must not raise NonFiniteValue for legitimately finite input — the
    # fault-injection guard must not false-positive on ordinary data.
    analyzer.compute_betti_numbers(tuple(coordinates), eps=1.0)
