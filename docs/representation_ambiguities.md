# `cle.representation`: where the design was ambiguous, and what was chosen

Source: `CLE-v2_改訂設計書_v0.3.md` (v0.3) unless stated; `RHC` =
`RepresentationHistoryContract_v1_設計書_v0.1.md`. Written during R0a/R0b so two
independent implementations can be compared point by point. Where a point is
ambiguous the verifier leans to UNVERIFIABLE, or the choice is stated as
"chosen"; each entry gives the section and the reason.

## A. Data model (R0a)

1. **Fields of `Ref` for `checker_output` and `history`** (§2.2). The design
   lists `checker_name`, `checker_version`, `output_sha256` / `history_id`,
   `history_hash` but gives `Ref` only `kind` and `value`. Chosen: `value`
   holds `output_sha256` / `history_hash`; extra optional `name`, `version`
   hold the checker name and version, or the `history_id`.
2. **`task_ref`** (§2.5, §2.7) has no type. Chosen: a plain string.
3. **`abandoned_branches[]`** (§2.7) has no shape. Chosen: `AbandonedBranch`
   (`branch_id`, `state_ids`, `morphism_ids`).
4. **Canonicalization**: §2.1 says "JCS", the task says sorted keys,
   `(",", ":")`, `ensure_ascii=False`. Chosen: the latter (no floats; floats
   raise `TypeError`). `preserved`/`lost`/vocabulary lists are treated as sets
   and sorted before hashing; states, morphisms, compositions and branches are
   sorted by id, so recording order does not change an ID. Evidence lists keep
   their order.
5. **IDs are not enforced** (§2.1 "[提案]"). `compute_id()` exists, but no rule
   checks that `morphism_id == compute_id()`. Likewise `history_hash` is
   computed by `seal()`, not verified by any rule.
6. **Enum values** are validated at construction (`RepresentationError`).
   Chosen so a misspelt `role` cannot silently pass as a non-identity.
7. **Identity generator** (§2.6): the verifier-made identity carries
   `verification="UNVERIFIED"` and `invertibility` "unknown" (its own id would
   otherwise depend on itself). Unit-law compositions with identities are
   derived in the checks, never added to the table.
8. **`carry` for an identity** that has `carry=null` is read as the identity map
   on its `preserved` set (R3). A non-identity with `carry=null` is
   CARRY_MISSING.

## B. Rules (R0b)

9. **Several results per rule.** §4 gives `CheckResult` one status and one
   reason code, but a rule can find several things. Chosen: one result per
   distinct `(status, reason_code)` with all its locations, FAIL before
   UNVERIFIABLE; exactly one PASS result when nothing was found. A rule is PASS
   only if it found neither FAIL nor UNVERIFIABLE.
10. **FAIL reason codes** are not enumerated in the design. Chosen (stable
    strings): DUPLICATE_ID, ENDPOINT_MISMATCH, COMPOSITION_ENDPOINT_MISMATCH,
    DUPLICATE_IDENTITY, COMPOSITION_NOT_FUNCTIONAL, UNIT_LAW_VIOLATION,
    ASSOCIATIVITY_VIOLATION, IDENTITY_MALFORMED, PRESERVED_NOT_CARRIED,
    LOST_NOT_PROPAGATED, INVERTIBLE_WITH_LOSS, INVERSE_ENDPOINT_MISMATCH,
    INVERSE_NOT_IDENTITY, VERIFIED_ON_REFUTED, RULE_SEAL_FAILED,
    VERIFIED_WITHOUT_EVIDENCE, CYCLE, ELEMENT_DROPPED, BRANCH_DROPPED,
    SPAN_ORDER, SPAN_ON_INELIGIBLE, FUNCTOR_ENDPOINT_MISMATCH,
    FUNCTOR_IMAGE_UNRESOLVED, FUNCTOR_COMPOSITION_NOT_PRESERVED,
    IDENTITY_NOT_PRESERVED, FINITE_CATEGORY_REJECTED. Extra UNVERIFIABLE code:
    MORPHISM_UNRESOLVED (a composition names a morphism the history lacks).
11. **Location of a composition** (§4 "Composition の組") is
    `Location("composition", "<first>|<second>", field)`.
12. **R1 and the existing `FiniteCategory`** (§3 R1). R1 does its own checks so
    every finding has a location; the wrapper `finite_category_of()` returns the
    category or a FAIL result (`FINITE_CATEGORY_REJECTED`) instead of raising,
    and is not part of R1's verdict.
13. **R2 "mechanically made composite"** (§2.4, §3.2) has no operational test.
    Chosen: a composition result with `role="composite"` is mechanical. R2 is
    UNVERIFIABLE (COMPOSITE_BY_CONSTRUCTION) unless at least one composition has
    a result that is neither `composite` nor `identity`. Composite results still
    take part in the table lookups; they are not removed.
14. **R2 composable pairs**: every ordered pair of non-identity morphisms with
    matching middle state must have a table entry, else COMPOSITION_UNDEFINED.
    Identity terms are derived (§2.6) and never required. Associativity is
    checked only on triples whose four intermediate lookups all exist.
15. **Several identities for one state** → FAIL (DUPLICATE_IDENTITY); the design
    does not say.
16. **R3 vocabulary mismatch**: `history.vocabulary_ref.value` must equal
    `vocabulary.ref.value`, else VOCABULARY_UNRESOLVED. A name used by a
    morphism but absent from the vocabulary is also VOCABULARY_UNRESOLVED.
17. **R3 namespaces**: `lost` holds information names (§2.3) but "undeclared"
    (§2.5) speaks of properties being in `lost`. Chosen: a property counts as
    declared if it is in `preserved` or `lost`; `carry` keys/values and
    `carry⁻¹(lost(g))` treat property and information names as one namespace.
    Undeclared properties are only reported for morphisms that appear in a
    composition.
18. **R3 partial `carry`**: a property in `preserved(h)` and `preserved(f)` with
    no `carry` entry → CARRY_MISSING (not FAIL).
19. **R3 on identities**: an identity must list the vocabulary's properties in
    `preserved` and have empty `lost` (§2.3); otherwise FAIL IDENTITY_MALFORMED.
20. **R4 when no term exists**: neither `g∘f` nor `f∘g` in the table →
    INVERSE_UNRESOLVED; exactly one missing → INVERSE_ONE_SIDED with the missing
    side in `field` (`g_after_f` or `f_after_g`). Wrong endpoints of the named
    inverse → FAIL INVERSE_ENDPOINT_MISMATCH.
21. **R4 "恒等射"**: a table result counts as the identity if it is any
    `role="identity"` morphism on that state.
22. **R5 scope**: the null-`rule_ref` check applies to every non-identity
    morphism, not only `VERIFIED` ones (§2.3 "null は R5 で UNVERIFIABLE").
23. **R5 precedence** for a `VERIFIED` morphism: REFUTED evidence (FAIL) first,
    then a failed rule seal (FAIL), then missing seal info / theorem-name-only
    (UNVERIFIABLE), then lack of any SEAL_OK + checked evidence (FAIL).
    `validity=null` is read as UNCHECKED; `seal_status=null` is "not supplied".
    A `rule_ref` of a kind other than `hext` is not rejected (identities are
    exempt from needing one).
24. **R6 DAG**: edges are the morphisms except `identity` and `inverse_claim`
    (inverses would make every invertible pair a cycle). A non-identity
    self-loop is a cycle. The first version always yields NO_PRIOR_VERSION, so
    R6 can only be PASS from the second version on. Preservation compares states
    and morphisms by id, and a branch by id with its state/morphism ids as a
    subset. A `previous` whose recomputed hash differs from `prev_history_hash`
    is PREV_HISTORY_UNRESOLVED.
25. **R7 "順序が通る"**: chosen as (a) `0 <= p_start <= p_end` per span, and
    (b) for `generator`/`composite` morphisms between states in the *same*
    session, `source.p_start <= target.p_start`. Cross-session pairs are not
    ordered. A missing verdict for a session with a span is ELIGIBILITY_MISSING.
26. **R8 identity term** (§3 R8): the existing `Functor` has no identity check,
    so R8 checks it itself. IDENTITY_PRESERVATION_UNCHECKED is used when the
    target records no identity for the image state, so the term cannot be
    checked. Mapping of verifier-made identities is the caller's job (an
    unmapped identity is FUNCTOR_PARTIAL).
27. **Vacuous rules**: R3 with no compositions, R4 with no invertible claims,
    R5/R7 with nothing to check return PASS (nothing violated). Only R2 has an
    explicit design rule for emptiness.
28. **Aggregation scope** (§4): `aggregate` considers only the results given.
    `verify_history` runs R1–R7; R8 needs two histories and a map and is run
    separately, so an aggregate without R8 results says nothing about R8.
29. **`inputs_sha256`** hashes, per rule, exactly the arguments that rule took
    (R1/R2/R4/R5: the history; R3: + vocabulary; R6: + previous; R7: +
    eligibility; R8: both histories and both maps). It does not include the rule
    name or checker version, which are separate fields.
30. **Checker version** is `"<cle version>+representation-r0"`.
