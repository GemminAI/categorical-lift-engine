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

## Phase 3 — Knowledge Crystallization Pipeline (RFC-CLE003)

Directive for this phase: implement the three existing, still-unimplemented
Protocols (`KnowledgeCrystallizer`, `KnowledgeDeltaGenerator`,
`CommitCandidateBuilder`) exactly as they already stand — no new ABI type,
no new Protocol, no new `KnowledgeDeltaKind` member. Unlike Phases 1–2, this
phase needed **zero** additive ABI surface: the mission's own four-step
breakdown (ConceptCandidate generation / confidence / KnowledgeDelta
generation / CommitCandidate generation) already maps onto the three
existing Protocols without modification, once RFC-CLE003 §3's Stage 3
(Symmetry Reduction) and Stage 4 (Multi-Context Pullback) — which need
multiple HEKB contexts to compare against, Enterprise-tier per RFC-CLE001
§2 — are scoped out, matching how the mission itself already scoped the
four steps down from RFC-CLE003's full five-stage pipeline.

| Mission step | Resolution |
|---|---|
| Step 1 (ConceptCandidate generation) | `cle.crystallization.ProvenanceCanonicalizingCrystallizer` implements the pre-existing `KnowledgeCrystallizer.crystallize(artifact) -> Artifact` unchanged. The "candidate" *is* the finalized `Artifact` — no new `ConceptCandidate` type was introduced. Scoped to the one meaningful, single-artifact finalization action: deduplicating `provenance` (first-occurrence order, not sorted — sorting would discard whatever sequencing the upstream stage encoded). |
| Step 2 (confidence estimation) | No separate Protocol — folded entirely into `CommitCandidateBuilder`, since `KnowledgeDelta` has no confidence field and `HEKBCommitCandidate.confidence` is the only place it can go. |
| Step 3 (KnowledgeDelta generation: NEW/UPDATE/MERGE/REINFORCE) | `cle.knowledge_delta.ArtifactKnowledgeDeltaGenerator` implements the pre-existing `KnowledgeDeltaGenerator.generate(artifact) -> KnowledgeDelta` unchanged, mapped onto the ABI's existing four `KnowledgeDeltaKind` members. NEW -> `CONCEPT_CREATED`, UPDATE -> `CONCEPT_UPDATED`. REINFORCE is **not** a separate kind — it is a `CONCEPT_UPDATED` delta whose `ConceptDelta.reinforcement_count` is the already-observable reinforcement signal, per direction. MERGE has **no representation**: `CATEGORY_RELATED` is a morphism between two categories, not a fusion of them, and RFC-CLE004 (Phase 4, Category Evolution Tracking) is where MERGE actually belongs (its own BIRTH/DEATH/MERGE/SPLIT/DRIFT taxonomy) — deferred there, not fabricated here. |
| Step 4 (CommitCandidate generation) | `cle.commit_candidate.ObservationalCommitCandidateBuilder` implements the pre-existing `CommitCandidateBuilder.build(delta, *, source_trajectory_id) -> HEKBCommitCandidate` unchanged. Confidence is a deterministic, monotonic, saturating function (`evidence / (evidence + half_life)`) of observable evidence already on the delta's payload — `dwell_steps` (Concept), `reinforcement_count` (ConceptDelta), `len(concept_ids)` (Category) — never a topological signal (Betti numbers still have no ABI home, still deliberately deferred). `CategoryRelation` gets a fixed confidence of `1.0`: it only exists because a `FunctorConstructor` already *proved* the mapping holds, so its existence is a validated fact, not a volume-of-evidence estimate. |
| `HEKBCommitCandidate.created_at_ns` vs. "no timestamps" | Resolved via an injectable `clock_ns: Callable[[], int]` constructor field (default `time.time_ns`). The determinism guarantee actually tested is scoped to `id`/`delta`/`confidence`/`provenance` — not `created_at_ns`, which records *when*, not *what*, and cannot be deterministic without lying about it. |

No ABI file changed: `git diff` against `src/cle/abi/` for this phase is
empty.

### Phase 3 addendum — architectural review finding, fixed

An architecture-only review (additive Protocol growth, ABI consistency,
mathematical correctness claims, determinism, unnecessary abstraction)
found one real, empirically-reproduced issue in
`ObservationalCommitCandidateBuilder`, fixed as an experimental validation
improvement — not an architectural change, no ABI/Protocol/behavior surface
touched beyond the one new check:

**Unvalidated `confidence_half_life` precondition.** The confidence
formula's monotonicity claim ("strictly increasing for `evidence >= 0`,
`half_life > 0`") is correct, but `half_life > 0` was never enforced.
Reproduced three concrete failure modes: `confidence_half_life=0.0` with
positive evidence silently returns `confidence=1.0` for *any* evidence
value (stops depending on evidence at all); `confidence_half_life=0.0`
with zero evidence raises `ZeroDivisionError`; `confidence_half_life<0`
pushes the result outside `[0, 1]`, which then surfaces several calls
later as `HEKBCommitCandidate.__post_init__`'s existing bounds-check
`ValueError` — a confusing, indirect failure that never names the actual
misconfiguration.

Fixed with a `__post_init__` on `ObservationalCommitCandidateBuilder`
(the same validate-at-construction convention `Category`/`KnowledgeDelta`/
`HEKBCommitCandidate` already use elsewhere in this ABI) raising
`ValueError("confidence_half_life must be greater than zero")` immediately
at construction. No change to the confidence formula, deterministic id
generation, the injected clock, or any ABI/Protocol — purely an added
precondition check. 3 new regression tests (0.0 and negative rejected at
construction; a valid positive value's existing behavior unchanged).

## Phase 4 — Category Evolution Tracking (RFC-CLE004) — experimental

Explicit change of directive for this phase, stated up front rather than
discovered by contrast with Phases 1–3: those phases optimized for the
smallest possible ABI footprint, implementing existing Protocols and adding
new surface only when "strictly required." Phase 4 optimizes for the
opposite — discovering the right shape for knowledge-evolution tracking by
actually building RFC-CLE004's intermediate representations, not by
minimizing what gets added. Git history is the stated safety net for this:
every type below is expected to be revised or removed as the discovery
continues, and none of them are load-bearing for Phases 1–3.

### What was added, and why it's self-contained

Everything lives in one new module, `cle.evolution`, deliberately kept
*outside* `cle.abi` — unlike Phase 1's `ConceptMorphism`/`MorphismType`
(added to `cle.abi.outputs` because they were judged stable enough to join
the core ABI), Phase 4's types are explicitly provisional. Deleting
`src/cle/evolution/` and `tests/test_evolution.py` entirely would not
change one line of `cle.abi`, `cle.concept`, `cle.homotopy`,
`cle.crystallization`, `cle.knowledge_delta`, or `cle.commit_candidate` —
verified by construction, not just claimed (the only imports *into*
`cle.evolution` are `cle.abi.inputs.Vector`, `cle.abi.outputs.MorphismType`,
`cle.geometry.euclidean_distance`, and `cle.identity.deterministic_id` —
all one-directional; nothing outside `cle.evolution` imports from it).

| RFC-CLE004 concept | Resolution |
|---|---|
| `EvolutionEventType` (BIRTH/DEATH/MERGE/SPLIT/DRIFT) | Added verbatim, all five members, matching RFC-CLE004 §4 exactly. Only `BIRTH`/`DEATH`/`DRIFT` are constructible by this milestone's tracker — `MERGE`/`SPLIT` need a pushout/pullback mechanism this milestone doesn't build (see below). |
| `AncestryLink` | Added, with `morphism_type` typed as Phase 1's existing `cle.abi.outputs.MorphismType` rather than a second, parallel string vocabulary — RFC-CLE004's own examples ("canonical_inclusion", "pushout_projection") already map onto `INCLUSION`/`PUSHOUT_CANONICAL`. |
| `EvolutionEvent` | Added close to RFC-CLE004 §4's shape, with `betti_delta: tuple[int, ...]` finally giving `cle.homotopy`'s Betti numbers a place to travel — the exact gap flagged and deliberately deferred in the Phase 2 and Phase 3 reviews. This milestone always sets it to `()`: computing a real delta needs each node's trajectory, which `NodeState` (below) doesn't carry. The field exists now so a later milestone can populate it without another type-shaped change. `confidence_score` is bounds-validated at construction (`__post_init__`), matching the `Category`/`KnowledgeDelta`/`HEKBCommitCandidate` convention already established in the ABI proper. |
| `LineageSnapshot` | Added verbatim (ids + parent pointer only, no geometry) — RFC-CLE004's own design is already minimal here, and there was no reason to enrich it: `NodeState` is where geometry lives. |
| **New, not in RFC-CLE004**: `NodeState` (`node_id`, `centroid`) | RFC-CLE004 §5's `detect_evolution(previous_snapshot, current_lift_objects: Sequence[Any], current_lift_morphisms: Sequence[Any])` leaves "lift objects" unspecified. Using `Concept \| ConceptDelta` directly doesn't work: a `ConceptDelta` only carries a *shift*, not an absolute position, so the previous absolute centroid isn't reconstructable from a `ConceptDelta` alone, and `LineageSnapshot.active_node_ids` carries no geometry at all. `NodeState` is the smallest representation that makes BIRTH/DEATH/DRIFT detection well-defined and testable — introduced exactly because "optimize for discovery" invites it, not smuggled in as a minimal necessity. |
| `CategoryEvolutionTrackingProtocol.detect_evolution` / `apply_events` | Added as `CategoryEvolutionTracker.detect_evolution(previous_nodes, current_nodes) -> tuple[EvolutionEvent, ...]` / `apply_events(previous_snapshot, events) -> LineageSnapshot`, implemented by `GeometricEvolutionTracker`. Signature adapted from RFC-CLE004's literal one: `detect_evolution` takes `tuple[NodeState, ...]` pairs instead of a `LineageSnapshot` (id-only, insufficient for DRIFT's geometry) plus untyped object/morphism sequences. |
| `CategoryEvolutionTrackingProtocol.trace_lineage` | **Not added yet.** With only BIRTH/DEATH/DRIFT producible, every node has at most one trivial parent — a lineage trace has nothing genuine to demonstrate before `MERGE`/`SPLIT` exist to create real multi-parent ancestry. Declaring it now would ship an untested, unmotivated method. Deferred to the same follow-up milestone as `MERGE`/`SPLIT`, added additively (this Protocol is brand new this phase, so there is no "existing shipped signature" being redesigned by extending it later). |
| `MERGE` / `SPLIT` | Not implemented. RFC-CLE004 §2.1–2.2 defines them via pullback/pushout diagrams over multiple concepts — a real mechanism, not a naming exercise, and building one honestly is its own milestone rather than a same-day addition. |
| Determinism (`timestamp_utc`) | Same resolution as Phase 3's `created_at_ns`: an injectable `clock_utc: Callable[[], str]` constructor field on `GeometricEvolutionTracker` (default: real UTC time). `EvolutionEvent.event_id` and `LineageSnapshot.snapshot_id` are both derived only from semantic content (`cle.identity.deterministic_id` over node ids / prior event ids), never from `timestamp_utc` — verified directly: two trackers with different injected clocks produce identical `event_id`s and different `timestamp_utc`s for the same detection. |
| Event ordering | `detect_evolution`'s returned tuple is sorted by `(event_type, source_node_ids, target_node_ids)`, not left in whatever order the input `NodeState` tuples or Python's set-difference iteration happened to produce — the same host/iteration-order independence lesson the Phase 2 review's tie-break fix established for `FunctorialConceptLift`, applied proactively here instead of found by a later review. |
| Configuration validation | `GeometricEvolutionTracker.drift_tolerance` is validated at construction (`__post_init__`, `>= 0.0`) — applying the Phase 3 review's lesson (`confidence_half_life`'s unvalidated precondition) proactively rather than waiting for it to be found again. Note the bound differs deliberately: `drift_tolerance = 0.0` is valid (means "any movement at all is drift"), where Phase 3's `confidence_half_life` required strictly `> 0` (it is a divisor that must never be zero); `drift_tolerance` is only ever a comparison threshold, not a divisor, so zero is safe and meaningful. |

### Independent testability / reviewability

24 new tests in `tests/test_evolution.py`, covering: ABI-shape construction
for all four new types, BIRTH/DEATH/DRIFT detection (including the
boundary — movement exactly at `drift_tolerance` is *not* drift), DRIFT
confidence monotonicity, `apply_events`' set arithmetic (including that
DRIFT never changes `active_node_ids`), determinism (fixed-clock
reproducibility, input-order independence, event-id/timestamp separation),
and the two new configuration-validation guards. 100% line + branch
coverage achieved without a second pass — no coverage-driven test
gymnastics were needed, a mild signal that the module's branching is
already about as simple as the problem allows.

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
