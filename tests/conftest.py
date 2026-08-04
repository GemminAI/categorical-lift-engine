"""Shared test fixtures: fakes satisfying CLE's input ABI by shape.

None of these import `msr` — they are independent structural stand-ins for
what Meaning Space Runtime would emit, exactly as `docs/BOUNDARIES.md`
requires: CLE is tested against the shape of the ABI, never against MSR's
implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

Vector = tuple[float, ...]
Matrix = tuple[tuple[float, ...], ...]


@dataclass(frozen=True, slots=True)
class FakeMeaningState:
    frame_id: str
    step_index: int
    time_s: float
    theta: Vector
    basin_id: str | None


@dataclass(frozen=True, slots=True)
class FakeStabilizedTrajectory:
    trajectory_id: str
    frame_id: str
    basin_id: str | None
    states: tuple[FakeMeaningState, ...]
    centroid: Vector
    covariance: Matrix
    dwell_steps: int
    dwell_seconds: float
    provenance: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_novel(self) -> bool:
        return self.basin_id is None


def make_state(
    step_index: int = 0, basin_id: str | None = "basin-1"
) -> FakeMeaningState:
    return FakeMeaningState(
        frame_id="F",
        step_index=step_index,
        time_s=float(step_index) * 0.1,
        theta=(1.0, 2.0),
        basin_id=basin_id,
    )


@pytest.fixture
def stabilized_trajectory() -> FakeStabilizedTrajectory:
    return FakeStabilizedTrajectory(
        trajectory_id="traj-1",
        frame_id="F",
        basin_id=None,  # novel: no known basin explained it
        states=(make_state(0), make_state(1), make_state(2)),
        centroid=(1.0, 2.0),
        covariance=((0.1, 0.0), (0.0, 0.1)),
        dwell_steps=3,
        dwell_seconds=0.3,
        provenance=("obs-1", "obs-2", "obs-3"),
    )


@pytest.fixture
def unstabilized_trajectory() -> FakeStabilizedTrajectory:
    return FakeStabilizedTrajectory(
        trajectory_id="traj-flowing",
        frame_id="F",
        basin_id=None,
        states=(),
        centroid=(0.0, 0.0),
        covariance=((1.0, 0.0), (0.0, 1.0)),
        dwell_steps=0,
        dwell_seconds=0.0,
    )


@dataclass(frozen=True, slots=True)
class FakeHEKBConcept:
    id: str
    centroid: Vector | None


@dataclass(frozen=True, slots=True)
class FakeHEKBContext:
    """A structural `HEKBContextLike`: returns whatever `near` was seeded with."""

    near: tuple[FakeHEKBConcept, ...] = field(default_factory=tuple)

    def concepts_near(
        self, centroid: Vector, *, radius: float
    ) -> tuple[FakeHEKBConcept, ...]:
        return self.near


@pytest.fixture
def reinforcing_trajectory() -> FakeStabilizedTrajectory:
    return FakeStabilizedTrajectory(
        trajectory_id="traj-2",
        frame_id="F",
        basin_id="basin-1",  # not novel: MSR already recognizes this basin
        states=(make_state(0, basin_id="basin-1"),),
        centroid=(1.1, 2.1),
        covariance=((0.1, 0.0), (0.0, 0.1)),
        dwell_steps=1,
        dwell_seconds=0.1,
        provenance=("obs-9",),
    )
