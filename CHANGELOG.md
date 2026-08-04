# Changelog

## Unreleased

### Added — Phase 4: Category Evolution Tracking (RFC-CLE004) — experimental

Explicit change of directive for this phase: optimize for discovering the
right shape for knowledge-evolution tracking, not for a minimal ABI. Every
type is new, deliberately kept outside `cle.abi`, and independently
removable — deleting `src/cle/evolution/` changes nothing in Phases 1–3.
Full rationale for every choice in `docs/RFC_ALIGNMENT.md`.

- `cle.evolution` (new module): `EvolutionEventType` (all five RFC-CLE004
  members: BIRTH/DEATH/MERGE/SPLIT/DRIFT — only the first three are
  constructible this milestone), `NodeState` (a node's id + position; not
  in RFC-CLE004, introduced because neither `LineageSnapshot` nor
  `ConceptDelta` alone carries what BIRTH/DEATH/DRIFT detection needs),
  `AncestryLink` (reuses Phase 1's `MorphismType`), `EvolutionEvent`
  (`betti_delta` finally gives `cle.homotopy`'s Betti numbers a place to
  travel, deferred since the Phase 2 review), `LineageSnapshot`.
- `CategoryEvolutionTracker` (new Protocol: `detect_evolution`,
  `apply_events` — `trace_lineage` deferred until `MERGE`/`SPLIT` exist to
  give it a real multi-parent case to prove) + `GeometricEvolutionTracker`:
  BIRTH (new node id), DEATH (missing node id), DRIFT (moved beyond
  `drift_tolerance`, Euclidean distance) detection from two `NodeState`
  sequences; `apply_events` replays them into a new `LineageSnapshot`.
  `MERGE`/`SPLIT` need a real pushout/pullback mechanism, not implemented
  yet.
- Determinism and validation lessons from the Phase 2/3 reviews applied
  proactively rather than found again: event ordering is sorted, not
  iteration-order-dependent; `event_id`/`snapshot_id` are content-addressed
  and verified independent of the injectable `clock_utc`; `drift_tolerance`
  is validated (`>= 0.0`) at construction.
- 24 new tests, 100% line + branch coverage, ruff clean, mypy `--strict`
  clean maintained (134 tests total, up from 110).

### Added — Phase 3: Knowledge Crystallization Pipeline (RFC-CLE003)

Zero ABI changes this phase — the mission's four steps (ConceptCandidate
generation / confidence / KnowledgeDelta generation / CommitCandidate
generation) already mapped onto the three existing, still-unimplemented
Protocols without modification. Full rationale in `docs/RFC_ALIGNMENT.md`.

- `cle.crystallization.ProvenanceCanonicalizingCrystallizer`: implements
  `KnowledgeCrystallizer.crystallize` — deduplicates an artifact's
  `provenance` (first-occurrence order), the one meaningful finalization
  action available from a single artifact.
- `cle.knowledge_delta.ArtifactKnowledgeDeltaGenerator`: implements
  `KnowledgeDeltaGenerator.generate` — maps `Concept`/`ConceptDelta`/
  `Category`/`CategoryRelation` onto the existing four `KnowledgeDeltaKind`
  values. REINFORCE is a `CONCEPT_UPDATED` delta distinguished by
  `reinforcement_count`, not a new kind. MERGE is out of scope, deferred to
  Phase 4 (RFC-CLE004 Category Evolution Tracking), where it actually
  belongs.
- `cle.commit_candidate.ObservationalCommitCandidateBuilder`: implements
  `CommitCandidateBuilder.build`. Confidence is a deterministic, strictly
  monotonic, saturating function of observable evidence already on the
  artifact (`dwell_steps`, `reinforcement_count`, `len(concept_ids)`);
  `CategoryRelation` gets a fixed `1.0` (its existence is already a proven
  fact, not a volume-of-evidence estimate). `created_at_ns` comes from an
  injectable `clock_ns` callable, keeping `id`/`delta`/`confidence`/
  `provenance` testable for "same input -> same output" independent of
  wall-clock time.
- 24 new tests, including explicit confidence-monotonicity and
  candidate/delta-reproducibility property tests. 100% line + branch
  coverage, ruff clean, mypy `--strict` clean maintained (107 tests total,
  up from 82).

### Fixed — Phase 3 architectural review

An architecture-only review found one real, reproduced issue in
`ObservationalCommitCandidateBuilder`'s confidence formula, fixed as an
experimental validation improvement (no architectural, ABI, or Protocol
change) — see `docs/RFC_ALIGNMENT.md`'s Phase 3 addendum.

- `confidence_half_life` is now validated at construction
  (`__post_init__` raises `ValueError("confidence_half_life must be
  greater than zero")` for `<= 0`). Previously, `0.0` silently made
  confidence stop depending on evidence (always `1.0` for any positive
  evidence) or raised `ZeroDivisionError` at zero evidence; negative
  values could push confidence outside `[0, 1]`, surfacing several calls
  later as an unrelated-looking `ValueError` from `HEKBCommitCandidate`'s
  own bounds check.
- 3 new regression tests (110 total): zero and negative rejected at
  construction; valid positive values behave exactly as before.

### Added — Phase 2: Homotopy Path Analyzer (RFC-CLE001 §3.3)

Correctness-first, minimum-mathematics implementation — no persistent
homology, no simplicial-complex library, per direction. Full rationale and
the documented scope limitation in `docs/RFC_ALIGNMENT.md`.

- `cle.homotopy.HomotopyPathAnalyzer` (new Protocol, additive alongside the
  pre-existing `HomotopyAnalyzer`, untouched) + `EpsilonGraphBettiAnalyzer`:
  `compute_betti_numbers` builds a single-scale eps-neighborhood graph
  (union-find) and returns `(b_0, b_1)` — connected-component count and
  circuit rank. `paths_are_homotopic` decides equivalence by Betti-tuple
  equality at a shared tolerance, documented as a necessary-condition
  proxy, not a full homotopy-equivalence decision procedure.
- `cle.geometry` (new module): `euclidean_distance`, shared by `cle.homotopy`.
- 16 new tests: mathematical validation against hand-verified graphs
  (single point, disconnected points, a genuine 4-cycle, and a
  mutually-close triangle that deliberately demonstrates this analyzer's
  documented upper-bound-on-`b_1` limitation), plus explicit invariance
  properties proving *why* `b_0`/`b_1` are invariant (translation,
  rotation, reflection, and point-reordering all preserve pairwise
  distances, hence the eps-graph, hence the Betti numbers — and a
  contrasting test confirming scale is *not* free the same way).
- 100% line + branch coverage, ruff clean, mypy `--strict` clean maintained
  (81 tests total, up from 65).

### Fixed — Phase 2 architectural review

An architecture-only review (additive Protocol growth, ABI consistency,
mathematical correctness claims, determinism, unnecessary abstraction, and
specifically whether `HomotopyPathAnalyzer` overlaps `HomotopyAnalyzer`)
found one real issue, fixed — see `docs/RFC_ALIGNMENT.md`'s Phase 2
addendum.

- Renamed `HomotopyPathAnalyzer.is_homotopic` (and
  `EpsilonGraphBettiAnalyzer`'s implementation) to `paths_are_homotopic`.
  It shared a method name with the differently-shaped, pre-existing
  `HomotopyAnalyzer.is_homotopic`, which made `@runtime_checkable`
  `isinstance(EpsilonGraphBettiAnalyzer(), HomotopyAnalyzer)` incorrectly
  return `True` (confirmed) — `runtime_checkable` only checks method names,
  not signatures. Pure rename, no behavior change.
- 1 new regression test (82 total) locking in
  `isinstance(EpsilonGraphBettiAnalyzer(), HomotopyAnalyzer)` being `False`.

### Added — Phase 1: Functorial Lift Engine (RFC-CLE001 §3.1)

First concrete categorical-theory implementations, against RFC-CLE001–005
(published 2026-08-04, after this repository's initial skeleton). Every
pre-existing Protocol/dataclass/module is unchanged; additions are called
out below and logged in detail in `docs/RFC_ALIGNMENT.md`.

- `cle.concept.FunctorialConceptLift`: object lifting — implements the
  existing `ConceptDiscoveryStrategy` Protocol. Novel trajectories lift to
  a new `Concept`; reinforcing trajectories resolve to a `ConceptDelta`
  against the nearest known HEKB concept (radius derived from the
  trajectory's own covariance), falling back to a `basin_id`-derived id
  when no host context is supplied.
- `cle.morphism` (new module): `MorphismLiftStrategy` Protocol +
  `IdentityInclusionMorphismLift` — morphism lifting. Every lifted concept
  carries its identity morphism; a matched prior concept additionally
  yields an inclusion morphism.
- `cle.functor.CanonicalInclusionFunctorConstructor`: functor construction —
  implements the existing `FunctorConstructor` Protocol as the canonical
  inclusion functor between two categories whose concept-id sets are
  subset-related.
- `cle.identity.deterministic_id` (new module): content-addressed id
  generation shared by all three implementations above, satisfying
  RFC-CLE005 §3.2's lift-determinism requirement.
- ABI additions (additive only, nothing renamed/removed):
  `cle.abi.outputs.ConceptMorphism`, `cle.abi.outputs.MorphismType`,
  `cle.errors.FunctorialityViolation`.
- 20 new tests; 100% line + branch coverage, ruff clean, mypy `--strict`
  clean maintained (63 tests total, up from 43).

### Fixed — Phase 1 architectural review

An architecture-only review (Protocol/ABI leakage, OSS/Pro boundary,
determinism, unnecessary abstraction) of the above found two
implementation-quality issues in `FunctorialConceptLift`, both fixed —
see `docs/RFC_ALIGNMENT.md`'s Phase 1 addendum for the full rationale.

- HEKB-candidate tie-break: `_closest_known_concept` now breaks exact
  distance ties by `.id`, so a match no longer depends on
  `hekb_context.concepts_near()`'s (host-controlled) return order.
- `cle.errors.InvalidTrajectory` (new): raised instead of hashing `None`
  into a concept id when a reinforcing trajectory has neither a
  `hekb_context` match nor a `basin_id` — `is_novel`/`basin_id` are
  independent properties on `StabilizedTrajectoryLike`, never assumed
  coupled.
- 2 new tests (65 total).

## 0.1.0 — 2026-08-04

### Added — initial skeleton

New, independent repository. Restores Categorical Lift as an independent
SensOS component after it was briefly integrated into Meaning Mapper and
reverted the same day (`meaning-mapper` CHANGELOG 2.0.0 → 2.1.0) once the
OSS/Pro product boundary made clear that measurement and knowledge
generation are different products, not just different modules.

- ABI (`cle.abi`): five structural input `Protocol`s
  (`StabilizedTrajectoryLike`, `MeaningStateLike`, `FieldPriorLike`,
  `HEKBConceptLike`, `HEKBContextLike`) mirroring `msr.abi`'s shapes
  without importing `msr`; six frozen output types (`Concept`,
  `ConceptDelta`, `Category`, `CategoryRelation`, `KnowledgeDelta`,
  `HEKBCommitCandidate`)
- Errors (`cle.errors`): `CLEError` and three subclasses (`NotStabilized`,
  `DimensionMismatch`, `NoStrategyConfigured`)
- Ports (`cle.ports`): `CommitSink` — the one outbound crossing, toward
  HEKB
- Nine stage interfaces, one `Protocol` each, no implementation:
  `cle.concept`, `cle.category`, `cle.homotopy`, `cle.quotient`,
  `cle.functor`, `cle.natural_transformation`, `cle.crystallization`,
  `cle.knowledge_delta`, `cle.commit_candidate`
- Orchestrator (`cle.categorical_lift.engine.CategoricalLiftEngine`):
  composes the nine stages into one `lift()` call; validates input
  stabilization, requires three minimum stages, treats the rest as
  optional skips rather than fabricated defaults
- `docs/ARCHITECTURE.md`, `docs/BOUNDARIES.md`, `docs/RFC_ALIGNMENT.md`
  (no `RFC-CLE` series exists yet — assumptions recorded, not asserted)
- Unit-test scaffolding: ABI validation, `Protocol` shape-conformance for
  every stage, and full orchestration coverage for `CategoricalLiftEngine`
  (required-stage enforcement, optional-stage skipping, category
  branching, crystallizer pass-through, commit-sink submission)
- Ruff clean, mypy `--strict` clean
- License status intentionally reserved — see `LICENSE`/`NOTICE`
