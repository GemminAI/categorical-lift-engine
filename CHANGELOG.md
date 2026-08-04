# Changelog

## Unreleased

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
