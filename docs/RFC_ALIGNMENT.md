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
