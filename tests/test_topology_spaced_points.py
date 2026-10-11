"""cle.topology.spaced_points -- SpacedPointSequence construction and the
one fixed MSR -> CLE space_id binding."""

from __future__ import annotations

import numpy as np
import pytest

from cle.errors import DimensionMismatch, NonFiniteValue
from cle.topology.spaced_points import SpacedPointSequence
from conftest import FakeStabilizedTrajectory


def test_from_stabilized_trajectory_fixes_space_id_to_msr_theta(
    stabilized_trajectory: FakeStabilizedTrajectory,
) -> None:
    sequence = SpacedPointSequence.from_stabilized_trajectory(stabilized_trajectory)
    assert sequence.space_id == "msr.theta"


def test_from_stabilized_trajectory_carries_frame_id_and_provenance_verbatim(
    stabilized_trajectory: FakeStabilizedTrajectory,
) -> None:
    sequence = SpacedPointSequence.from_stabilized_trajectory(stabilized_trajectory)
    assert sequence.frame_id == stabilized_trajectory.frame_id
    assert sequence.provenance == stabilized_trajectory.provenance


def test_from_stabilized_trajectory_points_match_each_state_theta(
    stabilized_trajectory: FakeStabilizedTrajectory,
) -> None:
    sequence = SpacedPointSequence.from_stabilized_trajectory(stabilized_trajectory)
    assert sequence.points.shape == (3, 2)
    for row, state in zip(sequence.points, stabilized_trajectory.states, strict=True):
        assert tuple(row) == state.theta


def test_from_stabilized_trajectory_order_is_step_index(
    stabilized_trajectory: FakeStabilizedTrajectory,
) -> None:
    sequence = SpacedPointSequence.from_stabilized_trajectory(stabilized_trajectory)
    assert sequence.order == (0, 1, 2)


def test_from_stabilized_trajectory_handles_empty_states(
    unstabilized_trajectory: FakeStabilizedTrajectory,
) -> None:
    sequence = SpacedPointSequence.from_stabilized_trajectory(unstabilized_trajectory)
    assert sequence.points.shape == (0, 0)
    assert sequence.order == ()


def test_direct_construction_rejects_non_2d_points() -> None:
    with pytest.raises(DimensionMismatch):
        SpacedPointSequence(
            space_id="nvs.hidden64",
            frame_id="F",
            points=np.zeros(4),
            order=(0, 1, 2, 3),
        )


def test_direct_construction_rejects_order_length_mismatch() -> None:
    with pytest.raises(DimensionMismatch):
        SpacedPointSequence(
            space_id="nvs.hidden64",
            frame_id="F",
            points=np.zeros((3, 64)),
            order=(0, 1),
        )


def test_direct_construction_rejects_non_finite_points() -> None:
    points = np.zeros((2, 3))
    points[0, 1] = float("nan")
    with pytest.raises(NonFiniteValue):
        SpacedPointSequence(
            space_id="nvs.hidden64", frame_id="F", points=points, order=(0, 1)
        )


def test_direct_construction_defaults_provenance_to_empty_tuple() -> None:
    sequence = SpacedPointSequence(
        space_id="nvs.hidden64", frame_id="F", points=np.zeros((1, 64)), order=(0,)
    )
    assert sequence.provenance == ()
