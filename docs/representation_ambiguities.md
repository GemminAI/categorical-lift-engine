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
3. **`abandoned_branches[]`** (§2.7) has no shape. Chosen: `AbandonedBranch` **[v0.4 D-25 で決定]**
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
7. **Identity generator** (§2.6): the verifier-made identity carries **[v0.4 D-05 で決定]**
   `verification="UNVERIFIED"` and `invertibility` "unknown" (its own id would
   otherwise depend on itself). Unit-law compositions with identities are
   derived in the checks, never added to the table.
8. **`carry` for an identity** that has `carry=null` is read as the identity map **[v0.4 D-21 で決定]**
   on its `preserved` set (R3). A non-identity with `carry=null` is
   CARRY_MISSING.

## B. Rules (R0b)

9. **Several results per rule.** §4 gives `CheckResult` one status and one **[v0.4 D-03, D-15 で決定]**
   reason code, but a rule can find several things. Chosen: one result per
   distinct `(status, reason_code)` with all its locations, FAIL before
   UNVERIFIABLE; exactly one PASS result when nothing was found. A rule is PASS
   only if it found neither FAIL nor UNVERIFIABLE.
10. **FAIL reason codes** are not enumerated in the design. Chosen (stable **[v0.4 v0.4「FAIL の理由コード」(docs/representation_fail_codes.md) で決定]**
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
11. **Location of a composition** (§4 "Composition の組") is **[v0.4 v0.4「場所の表記」 で決定]**
    `Location("composition", "<first>|<second>", field)`.
12. **R1 and the existing `FiniteCategory`** (§3 R1). R1 does its own checks so
    every finding has a location; the wrapper `finite_category_of()` returns the
    category or a FAIL result (`FINITE_CATEGORY_REJECTED`) instead of raising,
    and is not part of R1's verdict.
13. **R2 "mechanically made composite"** (§2.4, §3.2) has no operational test. **[v0.4 D-02 で決定]**
    Chosen: a composition result with `role="composite"` is mechanical. R2 is
    UNVERIFIABLE (COMPOSITE_BY_CONSTRUCTION) unless at least one composition has
    a result that is neither `composite` nor `identity`. Composite results still
    take part in the table lookups; they are not removed.
14. **R2 composable pairs**: every ordered pair of non-identity morphisms with **[v0.4 D-04, D-05 で決定]**
    matching middle state must have a table entry, else COMPOSITION_UNDEFINED.
    Identity terms are derived (§2.6) and never required. Associativity is
    checked only on triples whose four intermediate lookups all exist.
15. **Several identities for one state** → FAIL (DUPLICATE_IDENTITY); the design
    does not say.
16. **R3 vocabulary mismatch**: `history.vocabulary_ref.value` must equal **[v0.4 D-06 で決定]**
    `vocabulary.ref.value`, else VOCABULARY_UNRESOLVED. A name used by a
    morphism but absent from the vocabulary is also VOCABULARY_UNRESOLVED.
17. **R3 namespaces**: `lost` holds information names (§2.3) but "undeclared" **[v0.4 D-16 で決定]**
    (§2.5) speaks of properties being in `lost`. Chosen: a property counts as
    declared if it is in `preserved` or `lost`; `carry` keys/values and
    `carry⁻¹(lost(g))` treat property and information names as one namespace.
    Undeclared properties are only reported for morphisms that appear in a
    composition.
18. **R3 partial `carry`**: a property in `preserved(h)` and `preserved(f)` with **[v0.4 D-17 で決定]**
    no `carry` entry → CARRY_MISSING (not FAIL).
19. **R3 on identities**: an identity must list the vocabulary's properties in **[v0.4 D-10 で決定]**
    `preserved` and have empty `lost` (§2.3); otherwise FAIL IDENTITY_MALFORMED.
20. **R4 when no term exists**: neither `g∘f` nor `f∘g` in the table → **[v0.4 D-24 で決定]**
    INVERSE_UNRESOLVED; exactly one missing → INVERSE_ONE_SIDED with the missing
    side in `field` (`g_after_f` or `f_after_g`). Wrong endpoints of the named
    inverse → FAIL INVERSE_ENDPOINT_MISMATCH.
21. **R4 "恒等射"**: a table result counts as the identity if it is any
    `role="identity"` morphism on that state.
22. **R5 scope**: the null-`rule_ref` check applies to every non-identity **[v0.4 D-11 で決定]**
    morphism, not only `VERIFIED` ones (§2.3 "null は R5 で UNVERIFIABLE").
23. **R5 precedence** for a `VERIFIED` morphism: REFUTED evidence (FAIL) first, **[v0.4 D-19 で決定]**
    then a failed rule seal (FAIL), then missing seal info / theorem-name-only
    (UNVERIFIABLE), then lack of any SEAL_OK + checked evidence (FAIL).
    `validity=null` is read as UNCHECKED; `seal_status=null` is "not supplied".
    A `rule_ref` of a kind other than `hext` is not rejected (identities are
    exempt from needing one).
24. **R6 DAG**: edges are the morphisms except `identity` and `inverse_claim` **[v0.4 D-01, D-20 で決定]**
    (inverses would make every invertible pair a cycle). A non-identity
    self-loop is a cycle. The first version always yields NO_PRIOR_VERSION, so
    R6 can only be PASS from the second version on. Preservation compares states
    and morphisms by id, and a branch by id with its state/morphism ids as a
    subset. A `previous` whose recomputed hash differs from `prev_history_hash`
    is PREV_HISTORY_UNRESOLVED.
25. **R7 "順序が通る"**: chosen as (a) `0 <= p_start <= p_end` per span, and **[v0.4 D-08 で決定]**
    (b) for `generator`/`composite` morphisms between states in the *same*
    session, `source.p_start <= target.p_start`. Cross-session pairs are not
    ordered. A missing verdict for a session with a span is ELIGIBILITY_MISSING.
26. **R8 identity term** (§3 R8): the existing `Functor` has no identity check, **[v0.4 D-09, D-18, D-22, D-23 で決定]**
    so R8 checks it itself. IDENTITY_PRESERVATION_UNCHECKED is used when the
    target records no identity for the image state, so the term cannot be
    checked. Mapping of verifier-made identities is the caller's job (an
    unmapped identity is FUNCTOR_PARTIAL).
27. **Vacuous rules**: R3 with no compositions, R4 with no invertible claims,
    R5/R7 with nothing to check return PASS (nothing violated). Only R2 has an
    explicit design rule for emptiness.
28. **Aggregation scope** (§4): `aggregate` considers only the results given. **[v0.4 v0.4「集計の範囲」 で決定]**
    `verify_history` runs R1–R7; R8 needs two histories and a map and is run
    separately, so an aggregate without R8 results says nothing about R8.
29. **`inputs_sha256`** hashes, per rule, exactly the arguments that rule took
    (R1/R2/R4/R5: the history; R3: + vocabulary; R6: + previous; R7: +
    eligibility; R8: both histories and both maps). It does not include the rule
    name or checker version, which are separate fields.
30. **Checker version** is `"<cle version>+representation-r0"`.

## C. CLE v0.4 で決まった点と、その実装（`feature/representation-v04-v1`）

設計書 v0.4（Tomo 承認、2026-10-26）の D-01〜D-25。A の読みのままのものは試験で固定した（`tests/test_representation_v04.py`、
`tests/golden/representation_D*.json`）。

| D | 内容（A の実装） |
|---|---|
| D-01 | R6 の DAG は版の連鎖のみ。状態・射のグラフの循環は検査しない。版の連鎖が自分に戻れば `VERSION_CYCLE`（宣言された `history_hash` が前の版の名として現れる場合のみ作れる：実際のハッシュでは不動点が無い） |
| D-02 | 独立な記録：両入力が非恒等射で、結果の `role` が composite でも identity でもない。単位律の項は数えず、`COMPOSITE_BY_CONSTRUCTION` の場所にも挙げない |
| D-03, D-15 | 規則内のすべての所見を報告し、規則の結果は最悪値（変更なし） |
| D-04 | 宙に浮いた参照は、それを使う部分だけ UNVERIFIABLE（変更なし） |
| D-05 | 単位律は導出してよい。`derive_unit_compositions` が項を書き出す（`basis="recomputed"`、`source="verifier"`）。**`Composition` に `source` 欄を足した**（既定 `"unknown"`、正規 JSON に入るので、v0.3 実装との間で `inputs_sha256` が変わる） |
| D-06 | R3 は語彙の `Ref.seal_status` を読む（null → `SEAL_STATUS_MISSING`、`SEAL_FAIL` → `VOCABULARY_UNRESOLVED`） |
| D-07 | 封印・妥当性は `Ref` が持つ（`resolved_refs` は無い）（変更なし） |
| D-08 〜 D-11, D-13, D-16 〜 D-18, D-21 〜 D-24 | 変更なし（試験で固定） |
| D-12 | 検証器は入力の欠陥で例外を投げない。値の型の欠陥は FAIL `INPUT_TYPE_INVALID`（場所つき。**新しい理由コード**）。Hypothesis で壊れた履歴を生成して確認（見つかった例外は 0 件） |
| D-14 | R8 の写像の余分な項は無視し、`CheckResult.warnings` に `MAP_EXTRA_ENTRY`（場所つき）として報告する。**`CheckWarning` と `warnings` 欄を足した**。`FUNCTOR_PARTIAL` は source の要素に像が無いときだけ |
| D-19 | R5：`SEAL_FAIL` の証拠を持つ `VERIFIED` は FAIL（既存の `VERIFIED_WITHOUT_EVIDENCE`）。封印欠落・名前だけの所見も、あれば併せて報告 |
| D-20 | R6：同じ id で内容が違えば FAIL `ELEMENT_REWRITTEN`（**新しい理由コード**。状態か射かは場所の `kind` で区別）。比較は `to_dict()`（集合は整列済み）。枝は、前の版の状態 id・射 id が残っていること |
| D-25 | `AbandonedBranch` = `{branch_id, state_ids[], morphism_ids[]}`（型の docstring・試験・正規 JSON） |

### 曖昧で、UNVERIFIABLE か保守的な側に倒した点（v0.4 で追加）

31. **D-12 の範囲**：検証器（`check_r1`〜`check_r8`、`verify_history`、`derive_unit_compositions`）に適用する。
    レコードの構築（列挙値の誤りは `RepresentationError`）と `from_dict`（欄の欠落は `KeyError`）は、検証の前の段階で、
    この範囲に含めていない。
32. **D-20 の枝**：枝の「同じ内容」は、前の版の状態 id・射 id がすべて残っていること（増えるのは許す）。
33. **D-19 の理由コード**：証拠の封印が破れたときも、新しい名前を作らず `VERIFIED_WITHOUT_EVIDENCE` を使う。
34. **D-14 の警告**：`CheckResult.warnings` は規則のすべての結果に同じものが付く。
