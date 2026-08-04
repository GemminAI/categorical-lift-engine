# RFC Alignment

**No `RFC-CLE` document exists anywhere in the GemminAI vault as of this
repository's creation (2026-08-04).** The only trace of the series is a
forward reference in `meaning-mapper/docs/RFC_COMPLIANCE.md`: *"Categorical
Lift itself — and any future RFC-CLE series — belongs to the independent
Categorical Lift Engine, not this repository."* This document records the
assumptions this repository's structure makes about that not-yet-written
series, so they can be checked against the real RFCs once they exist,
rather than silently treated as authoritative.

This repository was implemented under this workspace's own governance rule
(`CLAUDE.md` / `REPOSITORY_CANONICAL.md`, from the sibling `RFCv3_draft`
workspace): *"Never implement directly from a Draft RFC."* Here there is
not even a Draft — so this is Implementation-first, matching the precedent
`meaning-space-runtime`'s own README sets ("Implementation → Experiment →
Verification → RFC. This repository contains the implementation... it does
not design it") for exactly this situation, except one step earlier: no RFC
exists yet to document.

## Expected series (assumed, not confirmed)

| RFC | Assumed scope | What this repository assumes in its place |
|---|---|---|
| `RFC-CLE001` Architecture | System boundary, module placement, position relative to MSR/HEKB | `docs/ARCHITECTURE.md`, `docs/BOUNDARIES.md` — the OSS-complete-without-CLE position, the nine-stage pipeline shape |
| `RFC-CLE002` ABI | Frozen input/output types, binary or structural boundary contract | `cle.abi.inputs` (structural `Protocol`s mirroring `msr.abi.StabilizedTrajectory`/`MeaningState`) and `cle.abi.outputs` (six frozen dataclasses) |
| `RFC-CLE003` Categorical Lift | The categorical-theory construction itself (functor, natural transformation, pullback, pushout, commutative diagram) | Interfaces only (`cle.homotopy`, `cle.quotient`, `cle.functor`, `cle.natural_transformation`) — **no algorithm is assumed or implemented** |
| `RFC-CLE004` Knowledge Crystallization | How a stabilized trajectory becomes committable knowledge | `cle.crystallization`, `cle.knowledge_delta`, `cle.commit_candidate` interfaces, and `CategoricalLiftEngine.lift()`'s fixed orchestration order |
| `RFC-CLE005` Validation | Test/benchmark protocols, analogous to `RFC-MSR06` | `tests/` scaffolding only — conformance-by-shape tests for every `Protocol`, and orchestration tests for `CategoricalLiftEngine`; no quantitative Pass Criteria are assumed, since none exist to align to |

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

## What happens when RFC-CLE001–005 are published

This document is expected to be replaced or substantially rewritten once
real RFCs exist: any assumption above that the published text contradicts
should be corrected in the code and flagged here, following this
workspace's established convention (see `RFCv3_draft/rfc/MSR/RFC_MSR_SERIES_INDEX.md`
§9 for the house style of recording — not silently resolving — a
spec/implementation mismatch) rather than silently reconciled.
