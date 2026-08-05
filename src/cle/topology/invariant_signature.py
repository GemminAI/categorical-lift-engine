"""Invariant signature — CLE v3 spec §4.1/§4.2, Stage 5 `extract_invariants`.

`InvariantSignature` is the CLE v3 ABI shape exactly: `betti_0`, `betti_1`,
`betti_2`, and `euler_characteristic = betti_0 - betti_1 + betti_2`. This
supersedes the CLE v2 shape (a bare `betti: tuple[int, ...]`) in place, per
the v3 directive's "modify existing implementations when it is the cleanest
solution" — v2 and v3 never coexist for the same object, so there is nothing
to keep side-by-side.
"""

from __future__ import annotations

from dataclasses import dataclass

from cle.abi.inputs import Vector
from cle.topology.simplicial import VietorisRipsComplex, betti_numbers


@dataclass(frozen=True, slots=True)
class InvariantSignature:
    """The homotopy-invariant fingerprint of a point cloud at scale eps."""

    betti_0: int
    betti_1: int
    betti_2: int
    euler_characteristic: int

    def matches(self, other: InvariantSignature) -> bool:
        """Equal signatures are necessary, not sufficient, for equivalence.

        Unequal Betti triples prove two spaces are not homotopy-equivalent;
        equal triples are evidence, not proof — the same caveat
        `EpsilonGraphBettiAnalyzer.paths_are_homotopic` already documents.
        """
        return (
            self.betti_0 == other.betti_0
            and self.betti_1 == other.betti_1
            and self.betti_2 == other.betti_2
        )

    @classmethod
    def from_betti(cls, betti: tuple[int, ...]) -> InvariantSignature:
        """Build from a `betti_numbers(...)` tuple, padding missing dimensions."""
        betti_0 = betti[0] if len(betti) > 0 else 0
        betti_1 = betti[1] if len(betti) > 1 else 0
        betti_2 = betti[2] if len(betti) > 2 else 0
        return cls(
            betti_0=betti_0,
            betti_1=betti_1,
            betti_2=betti_2,
            euler_characteristic=betti_0 - betti_1 + betti_2,
        )


def compute_invariant_signature(
    coordinates: tuple[Vector, ...], eps: float, *, max_dimension: int
) -> InvariantSignature:
    complex_ = VietorisRipsComplex(coordinates, eps, max_dimension=max_dimension)
    betti = betti_numbers(complex_, max_dimension=max_dimension)
    return InvariantSignature.from_betti(betti)


__all__ = ["InvariantSignature", "compute_invariant_signature"]
