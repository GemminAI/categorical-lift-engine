from __future__ import annotations

from dataclasses import dataclass, field

from cle.abi.outputs import (
    Concept,
    HEKBCommitCandidate,
    KnowledgeDelta,
    KnowledgeDeltaKind,
)
from cle.ports.commit import CommitSink


@dataclass
class FakeCommitSink:
    received: list[HEKBCommitCandidate] = field(default_factory=list)

    def submit(self, candidate: HEKBCommitCandidate) -> None:
        self.received.append(candidate)


def test_fake_commit_sink_satisfies_protocol() -> None:
    assert isinstance(FakeCommitSink(), CommitSink)


def test_fake_commit_sink_records_submissions() -> None:
    sink = FakeCommitSink()
    concept = Concept(id="c-1", frame_id="F", centroid=(1.0,), hessian=None)
    delta = KnowledgeDelta(
        id="kd-1", kind=KnowledgeDeltaKind.CONCEPT_CREATED, concept=concept
    )
    candidate = HEKBCommitCandidate(
        id="cand-1",
        delta=delta,
        confidence=0.9,
        source_trajectory_id="traj-1",
        created_at_ns=1,
    )

    sink.submit(candidate)

    assert sink.received == [candidate]
