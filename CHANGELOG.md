# Changelog

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
