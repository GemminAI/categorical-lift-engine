# RFC Alignment

**`RFC-CLE001`–`RFC-CLE005` (v1.0.0, 2026-08-04) are now published.** This
repository predates them (also created 2026-08-04, Implementation-first —
see below); this document originally recorded *assumptions* about a
not-yet-written series and now records the real, checked comparison,
following this workspace's convention of recording — not silently
resolving — a spec/implementation mismatch (`RFCv3_draft/rfc/MSR/RFC_MSR_SERIES_INDEX.md`
§9).

This repository was implemented under this workspace's own governance rule
(`CLAUDE.md` / `REPOSITORY_CANONICAL.md`, from the sibling `RFCv3_draft`
workspace): *"Never implement directly from a Draft RFC."* At the time
there was not even a Draft, so the repository was built Implementation-first,
matching the precedent `meaning-space-runtime`'s own README sets. The
RFC-CLE series is explicitly **Experimental**: its purpose is to drive
implementation experiments and validate the mathematical architecture, not
to freeze a specification the code must match verbatim. Per direction, this
repository's frozen ABI is not treated as immutable either — it evolves
additively, one documented step at a time, as each phase's implementation
reveals what the RFC's math actually requires.

## Structural mismatch found against the published RFCs

RFC-CLE002's literal data model (`ObjectNode`, `MorphismEdge`,
`CategoricalLiftResult`, `CLEQuarantineStage`, `EvolutionEvent`,
`LineageSnapshot`, `HEKBCommitTransaction`, …) and literal Protocol
signatures (`FunctorialLiftEngineProtocol.lift(trajectory, frame) ->
CategoricalLiftResult`, `HomotopyPathAnalyzerProtocol.compute_betti_numbers`,
`CategoryEvolutionTrackingProtocol.detect_evolution/apply_events/trace_lineage`,
`CrystallizationEvaluatorProtocol.evaluate_candidate/build_hekb_transaction`)
do not match this repository's pre-existing ABI/Protocols at all — different
names, different shapes, different error-handling philosophy (RFC-CLE002 §5
mandates a `quarantine_stage` field and forbids raising; this repository's
`cle.errors.CLEError` hierarchy raises). None of RFC-CLE002's named types
existed in `cle.abi` before Phase 1.

Resolution, per direction: implement the RFC's *mathematics* against this
repository's *existing* Protocols and dataclasses wherever the existing
shape can carry it, extend the ABI additively (new fields/types/modules,
never renaming or removing anything shipped) only where it genuinely
cannot, and log every such addition here, phase by phase, as it happens.

## Phase 1 — Functorial Lift Engine (RFC-CLE001 §3.1, §5 subsystem "LFE")

| RFC-CLE001/002 concept | Resolution in this repository |
|---|---|
| Object lifting ($\mathcal{M}_{\text{proj}} \to \mathcal{C}_{\text{concept}}$ on objects) | Implemented as `cle.concept.FunctorialConceptLift`, satisfying the pre-existing `ConceptDiscoveryStrategy` Protocol unchanged. Novelty follows `trajectory.is_novel` exactly as that Protocol's docstring already specified. |
| Deterministic object/morphism ids (RFC-CLE005 §3.2 lift-determinism) | New pure-function module `cle.identity.deterministic_id` (content hash, no randomness/wall-clock) — additive, no existing symbol touched. |
| Morphism lifting (RFC-CLE001 §3.1: morphisms of $\mathcal{M}_{\text{proj}}$ must be preserved into $\mathcal{C}_{\text{concept}}$) | **Genuine ABI gap**: nothing in the pre-existing output ABI represented a morphism between two concepts (`CategoryRelation` is scoped to morphisms *between two `Category` values*, not concepts — see its own docstring). Added additively: `cle.abi.outputs.ConceptMorphism` (new frozen dataclass) and `cle.abi.outputs.MorphismType` (new `StrEnum`, values copied 1:1 from RFC-CLE002 §2.1 for future serialization compatibility), plus a new module `cle.morphism` (`MorphismLiftStrategy` Protocol + `IdentityInclusionMorphismLift` implementation). Phase 1 only ever constructs `IDENTITY` (every lifted object's trivial self-morphism, a category axiom) and `INCLUSION` (evidence flowing from a matched prior HEKB concept). `HOMOTOPIC_EQUIVALENCE`, `PULLBACK_CANONICAL`, `PUSHOUT_CANONICAL` are declared but intentionally unconstructed — they need trajectory-level topology (Phase 2 HPIA) or multi-category structure (Phase 4 CET), not Phase 1's concern. |
| Functor construction | Implemented as `cle.functor.CanonicalInclusionFunctorConstructor`, satisfying the pre-existing `FunctorConstructor` Protocol unchanged. Given only two frozen `Category` values (a `concept_ids` set each — no explicit object-to-object mapping is part of the ABI), the only functor derivable without fabricating evidence is the canonical inclusion functor (`source.concept_ids ⊆ target.concept_ids`); functoriality then holds automatically. |
| RFC-CLE002 §5 quarantine-on-functoriality-violation | **Not adopted verbatim.** No `quarantine_stage` field was added to the ABI (that would touch `HEKBCommitCandidate`/`Category`/etc., a much larger additive surface than Phase 1 needs). Instead, added `cle.errors.FunctorialityViolation(CLEError)` — same failure condition, this repository's existing raise-based convention. Revisit if/when a later phase's quarantine needs force a real `quarantine_stage` field. |

None of the above renamed, removed, or changed the signature of anything
that shipped before Phase 1; `git diff` against the pre-Phase-1 commit
contains only additions to `cle.abi.outputs.__all__`/`cle.errors.__all__`
plus two brand-new modules (`cle.identity`, `cle.morphism`) and concrete
implementation classes added *beside* each Protocol they satisfy.

### Phase 1 addendum — architectural review findings, fixed

An architecture-only review of Phase 1 (Protocol/ABI leakage, OSS/Pro
boundary, determinism, unnecessary abstraction) surfaced two implementation-
quality issues in `cle.concept.FunctorialConceptLift`, both fixed in the
same phase rather than deferred:

1. **Tie-break determinism.** `_closest_known_concept`'s `min(known, key=...)`
   selected the nearest HEKB candidate by distance alone. Two candidates
   exactly tied on distance would resolve by whatever order
   `hekb_context.concepts_near()` happened to return them in — order that
   is host-implemented and outside CLE's control, so "same trajectory lifted
   twice" could pick a different match across calls even though nothing
   about the trajectory changed. Fixed by adding `.id` as a stable secondary
   sort key (`key=lambda c: (distance, c.id)`); RFC-CLE005 §3.2's
   determinism now holds regardless of host return order. Not an RFC or ABI
   change — an implementation-quality fix.
2. **`basin_id`/`is_novel` assumed coupled.** The fallback path (no
   `hekb_context` match) computed `deterministic_id("concept", frame_id,
   trajectory.basin_id)` without checking `basin_id is not None`.
   `StabilizedTrajectoryLike` defines `is_novel` and `basin_id` as
   independent properties — nothing in the real Protocol guarantees
   `basin_id is not None` whenever `is_novel` is `False`; that relationship
   only held in the test fixture. Fixed by raising the new
   `cle.errors.InvalidTrajectory(CLEError)` when a reinforcing trajectory
   has neither a `hekb_context` match nor a `basin_id` to fall back on,
   instead of silently hashing `None` into a fabricated (and
   over-collapsing — every such trajectory from a frame would hash to the
   same id) concept id.

## Phase 2 — Homotopy Path Analyzer (RFC-CLE001 §3.3, §5 subsystem "HPIA")

Directive for this phase: correctness over feature completeness, small
deterministic implementations validated by property tests, no topology
library, and only the minimum mathematics RFC-CLE002 actually requires. The
resolution below is scoped tightly to that.

| RFC-CLE002 concept | Resolution in this repository |
|---|---|
| `HomotopyPathAnalyzerProtocol.compute_betti_numbers(coordinates, eps) -> Tuple[int, ...]` | **New Protocol** `cle.homotopy.HomotopyPathAnalyzer`, additive alongside the pre-existing `HomotopyAnalyzer` (untouched) — see "genuine ABI/Protocol gap" below for why a new Protocol was needed rather than extending the old one. Concrete implementation: `EpsilonGraphBettiAnalyzer.compute_betti_numbers`. Parameter type is `tuple[Vector, ...]` (this ABI's existing plain-tuple convention) rather than RFC-CLE002's `npt.NDArray[np.float64]` — this repository has never taken a numpy-typed ABI value anywhere (`cle.abi`'s own docstring: "serialized without touching numpy"), so the RFC's ndarray parameter was not adopted verbatim. |
| Persistent homology / Betti number derivation | **Not implemented as such — deliberately.** Real persistent homology needs a filtration across multiple scales and a simplicial-complex boundary-matrix computation; that is the "topology library" this phase was told not to build. What is implemented instead: a *single-scale* graph (one vertex per point, an edge between any two points within `eps`) via union-find, then `b_0` = connected-component count (exact — provably equal to the full simplicial complex's `b_0` at that scale, since connectivity never depends on higher simplices) and `b_1` = `edges - vertices + components` (the graph's circuit rank — an exact graph-theoretic fact, not an approximation of a graph invariant, though see the next row for how it relates to the *simplicial* invariant of the same name). |
| RFC-CLE005 §2.2 "same Betti numbers ⇒ same `homotopy_hash`" / counter-example invalidation | `b_1` as computed here is a **documented upper bound** on the true Vietoris-Rips simplicial complex's `b_1`, not identical to it: three mutually-close points are counted as one cycle (no 2-simplex is ever filled in to cap it off), where a real simplicial-homology computation would report `b_1 = 0` there. `tests/test_homotopy_path_analyzer.py::test_three_mutually_close_points_report_a_spurious_cycle_by_design` demonstrates this discrepancy directly rather than leaving it as an unverified claim — the goal per direction was mathematical honesty about scope, not silently overclaiming a full topological invariant. |
| `HomotopyPathAnalyzerProtocol.is_homotopic(traj_a, traj_b, tolerance) -> bool` | Implemented as `HomotopyPathAnalyzer.paths_are_homotopic` (named differently from RFC-CLE002's literal `is_homotopic` — see the Phase 2 addendum below) — Betti-tuple equality at the shared `tolerance` used as `eps` for both trajectories. This is a **necessary-condition proxy**, stated as such: Betti numbers are homotopy invariants, so *unequal* Betti numbers is a proof of non-homotopy-equivalence; *equal* Betti numbers is evidence, not proof (distinct spaces can share Betti numbers). RFC-CLE001 §3.3's literal "continuously deformable" test is not decided in general (that is undecidable/intractable for arbitrary point clouds) — this proxy is the minimum mathematics that satisfies what RFC-CLE005 §2.2 actually checks. |
| Genuine ABI/Protocol gap (flagged in the original gap analysis, now resolved) | The pre-existing `HomotopyAnalyzer.is_homotopic(a: HEKBConceptLike, b: HEKBConceptLike)` cannot carry this phase's math — `HEKBConceptLike` exposes only `.id`/`.centroid`, never a coordinate path, and no amount of implementation cleverness recovers topology from two points. Rather than widening that Protocol's signature (which would be a breaking change to something already shipped and reviewed), a new, separately-scoped Protocol was added. `HomotopyAnalyzer` stays exactly what it always was: a coarser, cheaper "same crystallized HEKB concept?" check with no coordinate data available, useful at a different point in the pipeline (post-crystallization) than `HomotopyPathAnalyzer` (pre-crystallization, still has the raw trajectory). |
| Shared geometry helper | New module `cle.geometry` (`euclidean_distance`), used only by `cle.homotopy`. Phase 1's `cle.concept` keeps its own private, near-identical helper rather than being refactored to share this one — each phase's already-reviewed code stays untouched; a few duplicated lines were judged cheaper than reopening a committed file for a cross-phase deduplication. |

None of the above changed the signature or behavior of anything that
shipped in Phase 1: `HomotopyAnalyzer` is byte-for-byte what it was, and
`cle.concept`/`cle.functor`/`cle.morphism` are untouched by this phase.

### Phase 2 addendum — architectural review finding, fixed

An architecture-only review of Phase 2 (additive Protocol growth, ABI
consistency, mathematical correctness claims, determinism, unnecessary
abstraction — explicitly checking whether `HomotopyPathAnalyzer` overlaps
`HomotopyAnalyzer`'s responsibilities) surfaced a real, empirically-confirmed
issue, fixed in the same phase:

**`is_homotopic` name collision causing a `runtime_checkable` false
positive.** `HomotopyPathAnalyzer.is_homotopic(traj_a, traj_b, tolerance)`
(RFC-CLE002's literal name) shared a method name with the pre-existing,
differently-shaped `HomotopyAnalyzer.is_homotopic(a, b)`. `@runtime_checkable`
`Protocol.__instancecheck__` only verifies that a method of the given
*name* exists on an object — it does not check parameter count or types.
Confirmed directly: `isinstance(EpsilonGraphBettiAnalyzer(), HomotopyAnalyzer)`
returned `True`, even though calling it as a `HomotopyAnalyzer` immediately
raises `TypeError: missing 1 required positional argument: 'tolerance'`.
This is a real hazard specifically because this codebase's own convention
(every file under `tests/test_stage_protocols.py`) is to verify Protocol
conformance via `isinstance` — a misconfigured injection could pass that
check and still crash at the call site.

This was not a responsibility overlap — `HomotopyAnalyzer` (post-
crystallization, id/centroid only) and `HomotopyPathAnalyzer`
(pre-crystallization, full coordinate path) remain two genuinely different
jobs, and stay two separate Protocols. Fixed by renaming
`HomotopyPathAnalyzer.is_homotopic` to `paths_are_homotopic` (and the
matching method on `EpsilonGraphBettiAnalyzer`) — a pure rename, no
behavior change. `test_betti_analyzer_does_not_falsely_satisfy_homotopy_analyzer`
locks in `isinstance(EpsilonGraphBettiAnalyzer(), HomotopyAnalyzer)` being
`False` going forward.

Noted, not fixed (by direction — deferred, not forgotten): the same
category of risk pre-dates this phase — `CategoryConstructor.construct` and
`FunctorConstructor.construct` (both Phase 0/1) collide exactly the same
way, confirmed the same way
(`isinstance(CanonicalInclusionFunctorConstructor(), CategoryConstructor)`
is also `True`). Phase 2 did not introduce this category of risk, it
surfaced a second instance of an existing one. Left alone per direction —
Betti-number ABI representation (RFC-CLE002's `ObjectNode.betti_numbers`)
is likewise deliberately deferred, to whenever a `TopologicalInvariant`-
shaped ABI addition is actually needed by Phase 3+'s
`Concept -> Knowledge` flow, not before.

## Assumptions carried from real, existing RFCs

Unlike the RFC-CLE series itself, these dependencies are real, published
documents this repository's design does align to:

- **`RFC-MSR01`** (`meaning-space-runtime`, Canonical/Standard) Section 2
  defines `StabilizedTrajectory` and `MeaningState` — `cle.abi.inputs`
  mirrors their field shapes exactly, as `Protocol`s, per Section 4's
  binding rule ("any object satisfying a port's shape MAY be bound").
- **`RFC-HEKB00`** v1.1 Principle 3 (Provenance) and Principle 9 (Knowledge
  Promotion Shall Be Monotonic) motivate `HEKBCommitCandidate` being a
  *proposal* rather than a write, and every output type carrying
  `provenance`.
- **`msr.adapters.hekb.ConceptLike`** (in `meaning-space-runtime`, not an
  RFC but a real, running structural contract) already expects a
  HEKB-sourced concept to expose `.id`, `.centroid`, and optionally
  `.hessian`/`.invariants`. `cle.abi.outputs.Concept` is shaped to satisfy
  it, so a `Concept` this repository eventually commits into HEKB can, once
  round-tripped, become a field-prior well for MSR again — without either
  repository importing the other.

## Ongoing convention for Phases 2–5

Each remaining phase (HPIA, KCP, CET, Validation) gets its own dated section
above, appended in the same shape as Phase 1's: which RFC concept it
targets, how it was resolved against the existing ABI, exactly what was
added (if anything), and what was deliberately left out and why. The
experiment is expected to keep surfacing mismatches like Phase 1's; they are
recorded here as they're found, not resolved by silently reconciling the
code to the RFC text or vice versa — per direction, implementation precedes
standardization, and the RFCs are expected to be refined based on these
empirical results, not the other way around.
