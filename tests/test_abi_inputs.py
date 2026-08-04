from __future__ import annotations

from cle.abi.inputs import (
    HEKBConceptLike,
    MeaningStateLike,
    StabilizedTrajectoryLike,
)
from conftest import FakeMeaningState, FakeStabilizedTrajectory, make_state


def test_fake_meaning_state_satisfies_protocol_by_shape() -> None:
    state = make_state()
    assert isinstance(state, MeaningStateLike)


def test_fake_stabilized_trajectory_satisfies_protocol_by_shape(
    stabilized_trajectory: FakeStabilizedTrajectory,
) -> None:
    assert isinstance(stabilized_trajectory, StabilizedTrajectoryLike)


def test_stabilized_trajectory_is_novel_when_no_basin(
    stabilized_trajectory: FakeStabilizedTrajectory,
) -> None:
    assert stabilized_trajectory.basin_id is None
    assert stabilized_trajectory.is_novel is True


def test_stabilized_trajectory_not_novel_with_known_basin() -> None:
    trajectory = FakeStabilizedTrajectory(
        trajectory_id="traj-2",
        frame_id="F",
        basin_id="basin-1",
        states=(
            FakeMeaningState(
                frame_id="F", step_index=0, time_s=0.0, theta=(0.0,), basin_id="basin-1"
            ),
        ),
        centroid=(0.0,),
        covariance=((0.1,),),
        dwell_steps=1,
        dwell_seconds=0.1,
    )
    assert trajectory.is_novel is False


def test_concept_satisfies_hekb_concept_like() -> None:
    from cle.abi.outputs import Concept

    concept = Concept(id="c-1", frame_id="F", centroid=(1.0,), hessian=None)
    assert isinstance(concept, HEKBConceptLike)
