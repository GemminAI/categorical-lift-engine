# FAIL reason codes of `cle.representation`

Fixed by CLE v0.4 ("FAIL の理由コード: A の名前を、docs の一覧に固定する"). The list is taken from the code
(`tests/test_representation_docs.py` compares it with the strings in `checks.py`); the descriptions are one line each.
UNVERIFIABLE reason codes are those of CLE v0.3 section 3 (plus `MORPHISM_UNRESOLVED`, see
`representation_ambiguities.md` #10). Warnings (not statuses) use `MAP_EXTRA_ENTRY` (R8, v0.4 D-14).
R9 (`check_obligation_transport`, not part of `verify_history`) also gives the UNVERIFIABLE codes `DECLARED_LOST_CONTRADICTED_BY_EVIDENCE`, `OBLIGATION_CARRY_MISSING`, `EVIDENCE_REF_MISSING`, `DECLARATION_CONTRADICTORY` and the existing `VOCABULARY_UNRESOLVED`, and the warnings `APPLICABILITY_UNDETERMINED` and `OBLIGATION_RESTORED`.

| code | meaning |
|---|---|
| `ASSOCIATIVITY_VIOLATION` | R2: two ways of composing three morphisms land on different recorded morphisms. |
| `BRANCH_DROPPED` | R6: a branch of the previous version is gone, or has lost state or morphism ids (v0.4 D-25). |
| `COMPOSITION_ENDPOINT_MISMATCH` | R1: a composition entry whose first, second and result do not chain (f: A->B, g: B->C, h: A->C). |
| `COMPOSITION_NOT_FUNCTIONAL` | R2: the same (first, second) pair is given two different results. |
| `DUPLICATE_ID` | R1: two states, or two morphisms, share an id. |
| `DUPLICATE_IDENTITY` | R2: a state has more than one identity morphism. |
| `ELEMENT_DROPPED` | R6: a state or morphism of the previous version is missing (location kind tells which). |
| `ELEMENT_REWRITTEN` | R6: a state or morphism keeps its id but its content differs from the previous version (v0.4 D-20). |
| `ENDPOINT_MISMATCH` | R1: an identity morphism whose source and target states differ. |
| `FINITE_CATEGORY_REJECTED` | R1: `finite_category_of` found that the existing `FiniteCategory` constructor rejects the history. |
| `FUNCTOR_COMPOSITION_NOT_PRESERVED` | R8: the image of a composition differs from the composition of the images. |
| `FUNCTOR_ENDPOINT_MISMATCH` | R8: a morphism's image does not run between the images of its endpoints. |
| `FUNCTOR_IMAGE_UNRESOLVED` | R8: an image names a state or morphism the target history does not contain (v0.4 D-22). |
| `IDENTITY_MALFORMED` | R3: an identity morphism does not preserve the whole vocabulary or loses information. |
| `IDENTITY_NOT_PRESERVED` | R8: an identity morphism is mapped to something that is not an identity of the image state. |
| `INPUT_TYPE_INVALID` | any rule: a value has a type other than the annotated one (v0.4 D-12); the location names the record. |
| `INVERSE_ENDPOINT_MISMATCH` | R4: the named inverse does not run from the target back to the source. |
| `INVERSE_NOT_IDENTITY` | R4: a composition of a morphism with its claimed inverse is not an identity. |
| `INVERTIBLE_WITH_LOSS` | R4: a morphism claimed invertible has a non-empty `lost`. |
| `LOST_NOT_PROPAGATED` | R3: `lost` of a composite lacks what was lost along the way. |
| `OBLIGATION_DECLARED_LOST` | R9 (M1, or M2 with no evidence): a stage declares an obligation property `lost`; location = the stage where it first drops (EXP-RAG-CTP001 v0.3 section 3). |
| `OBLIGATION_LOST_BY_EVIDENCE` | R9 (M2): the evidence says the property is lost (declared `lost`, or no declaration). |
| `PRESERVED_CONTRADICTED_BY_EVIDENCE` | R9 (M2): a stage declares the property `preserved` but the evidence says `lost`. |
| `PRESERVED_NOT_CARRIED` | R3: a composite claims a property preserved that the steps do not carry through. |
| `RULE_SEAL_FAILED` | R5: the rule reference of a VERIFIED morphism has `SEAL_FAIL`. |
| `SPAN_ON_INELIGIBLE` | R7: a state has a span in a session reported ineligible. |
| `SPAN_ORDER` | R7: a span has p_start < 0 or p_start > p_end, or a generator/composite morphism runs backwards in its session. |
| `UNIT_LAW_VIOLATION` | R2: an explicit unit-law entry does not give the morphism itself. |
| `VERIFIED_ON_REFUTED` | R5: a VERIFIED morphism cites evidence whose validity is REFUTED. |
| `VERIFIED_WITHOUT_EVIDENCE` | R5: a VERIFIED morphism has no evidence, or none that is sealed and checked, or has evidence with a broken seal (v0.4 D-13, D-19). |
| `VERSION_CYCLE` | R6: the chain of versions (`prev_history_hash`) returns to a version already on it (v0.4 D-01). |

## R9: where the constraint of a property comes from

R9 takes the constraint of an obligation from the `constraints` entries of the
vocabulary it is given (`(property, constraint id)` pairs, part of the vocabulary's
content and so under the same reference and seal check as its names). It never reads
a name (`c1.modality` and `path:...` are both opaque), a `path_label` or any other
key. `applicability` is keyed by constraint id. An obligation whose entry cannot be
read is `VOCABULARY_UNRESOLVED` (UNVERIFIABLE) with `detail.reason` and
`detail.property`: `PROPERTY_NOT_IN_VOCABULARY`, `CONSTRAINT_ENTRY_MISSING`,
`CONSTRAINT_ENTRY_DUPLICATE` (the same entry twice) or `CONSTRAINT_ENTRY_CONFLICT`
(two constraint ids for one name). These are values of `detail`, not new reason codes.

## R9: known limits

* **A vocabulary whose entries were rewritten cannot be told apart.** The check is on
  the `kind` and `value` of the reference (below), so a vocabulary with the same
  `kind` and `value` but other `constraints` entries is accepted as the same one.

* **The vocabulary check compares references, not content.** R9 accepts the vocabulary
  it is given when its `Ref` has the same `kind` and `value` as the history's
  `vocabulary_ref` and both carry `SEAL_OK`. It uses no hash of the content, so a
  vocabulary whose content was revised under the same `kind` and `value` cannot be
  told apart: give a revised vocabulary a new id. A reference fixed by the content
  (the HEXT v2 `state_hash`) is future work.
* **No cryptographic verification.** R9 only reads that the seal status is `SEAL_OK`;
  it does not verify the seal. A PASS from R9 does not mean the vocabulary is intact.
* **Independent of R3.** R9 judges from its own inputs and does not depend on R3's
  result for the history (a history for which R3 FAILs is still judged). If the
  vocabulary cannot be confirmed, the result is UNVERIFIABLE
  (`VOCABULARY_UNRESOLVED`), never PASS.
