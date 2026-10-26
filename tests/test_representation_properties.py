"""R2 against brute force on small finite categories, and reproducibility."""

from __future__ import annotations

import itertools

from hypothesis import given, settings
from hypothesis import strategies as st

from cle.representation import (
    Composition,
    RepresentationHistory,
    RepresentationMorphism,
    check_r2,
    verify_history,
)
from representation_builders import history, mor, state

SIZES = {"O1": 1, "O2": 2}


def _functions() -> list[tuple[str, str, tuple[int, ...]]]:
    out = []
    for a, b in itertools.product(SIZES, repeat=2):
        for image in itertools.product(range(SIZES[b]), repeat=SIZES[a]):
            out.append((a, b, image))
    return out


FUNCS = _functions()


def _name(fn: tuple[str, str, tuple[int, ...]]) -> str:
    return f"{fn[0]}{fn[1]}{''.join(map(str, fn[2]))}"


def _is_identity(fn: tuple[str, str, tuple[int, ...]]) -> bool:
    return fn[0] == fn[1] and fn[2] == tuple(range(SIZES[fn[0]]))


def _build(
    mutations: dict[int, int],
) -> tuple[RepresentationHistory, dict[tuple[str, str], str]]:
    """The category of maps between {0} and {0,1}, composition table optionally
    corrupted: entry i is redirected to the (mutations[i] mod n)-th parallel map."""
    morphisms: list[RepresentationMorphism] = []
    for fn in FUNCS:
        morphisms.append(
            mor(
                _name(fn),
                fn[0],
                fn[1],
                role="identity" if _is_identity(fn) else "generator",
            )
        )
    table: dict[tuple[str, str], str] = {}
    entries = []
    for f in FUNCS:
        for g in FUNCS:
            if f[1] == g[0] and not _is_identity(f) and not _is_identity(g):
                image = tuple(g[2][x] for x in f[2])
                entries.append((f, g, (f[0], g[1], image)))
    for index, (f, g, h) in enumerate(entries):
        if index in mutations:
            parallel = [p for p in FUNCS if (p[0], p[1]) == (f[0], g[1])]
            h = parallel[mutations[index] % len(parallel)]
        table[(_name(f), _name(g))] = _name(h)
    built = history(
        [state("O1"), state("O2")],
        morphisms,
        [Composition(a, b, r) for (a, b), r in table.items()],
        identities=False,
    )
    return built, table


def _brute_force_violates(
    h: RepresentationHistory, table: dict[tuple[str, str], str]
) -> bool:
    identity = {m.morphism_id for m in h.morphisms if m.role == "identity"}
    ends = {m.morphism_id: (m.source_state_id, m.target_state_id) for m in h.morphisms}

    def comp(f: str, g: str) -> str:  # g after f
        if f in identity:
            return g
        if g in identity:
            return f
        return table[(f, g)]

    names = list(ends)
    for f, g, k in itertools.product(names, repeat=3):
        chained = ends[f][1] == ends[g][0] and ends[g][1] == ends[k][0]
        if chained and comp(comp(f, g), k) != comp(f, comp(g, k)):
            return True
    return False


@settings(max_examples=60, deadline=None)
@given(st.dictionaries(st.integers(0, 40), st.integers(0, 7), max_size=6))
def test_r2_agrees_with_brute_force_associativity(mutations: dict[int, int]) -> None:
    h, table = _build(mutations)
    flagged = any(r.reason_code == "ASSOCIATIVITY_VIOLATION" for r in check_r2(h))
    assert flagged == _brute_force_violates(h, table)


def test_unmutated_category_is_associative_and_passes() -> None:
    h, table = _build({})
    assert not _brute_force_violates(h, table)
    assert [r.status for r in check_r2(h)] == ["PASS"]


@settings(max_examples=40, deadline=None)
@given(st.dictionaries(st.integers(0, 40), st.integers(0, 7), max_size=4))
def test_check_results_are_bit_identical_across_runs_and_reloads(
    mutations: dict[int, int],
) -> None:
    h, _ = _build(mutations)
    first = verify_history(h, eligibility={})
    again = verify_history(RepresentationHistory.from_dict(h.to_dict()), eligibility={})
    assert first == again
    assert [r.to_dict() for r in first] == [r.to_dict() for r in again]
    assert [r.inputs_sha256 for r in first] == [r.inputs_sha256 for r in again]
