# Experiment log

## 2026-09-09: prospective confirmation attrition margin

- Before creating the confirmation roster or observing any confirmation source,
  mutation, repair, or comparator outcome, the planned roster was increased from
  60 to 74 tasks.
- The final content-blind allocation is 8 tasks from each of five eligible
  ALFWorld train families (40 total) and all 34 eligible untouched ScienceWorld
  use-thermometer test variations.
- Reason: 30 ALFWorld tasks equaled the pre-registered minimum of 30 examples for
  the clobber and stale-validation classes before mutation validity was known.
  The larger roster provides prospective attrition margin without inspecting
  task content or outcomes.
- The minimum analysis gates remain unchanged; additional observations are not
  used to relax any threshold.

## 2026-09-09: topic selection

- Matrix cell: Skill reuse/composition x method/intervention.
- Paper 06 provides diagnosis but explicitly excludes repair. The new outcome
  is constrained native repair success, not diagnostic F1.
- Paper 06 confirmation tasks are development-only exposed evidence. Paper 13
  confirmation must exclude all task identifiers used by Papers 01--12.
- No Paper 13 native repair outcome existed when the development protocol was
  written.

## 2026-09-09: development revision 1 completed and rejected

- Revision 1 synthesized 399/403 exposed incidents and abstained on four
  ScienceWorld `rely_gap` incidents. The first native replay therefore covered
  399 incidents; its complete source snapshot, static predictions, and 399
  append-only trajectories were retained under
  `research/development_revisions/revision1/` and `results/development/native/`.
- Conflict-only native success was 178/252 (70.6%), below the registered 0.75
  gate. Role wrappers succeeded, but 24 ALFWorld and 30 ScienceWorld rely-gap
  repairs failed. The shortest clause-producing call restored possession but
  omitted objective-relevant cleaning, cooling, heating, or measurement steps.
- All 20 ScienceWorld clobber/stale incidents failed because the wrong-placement
  call terminated the episode before the post-clobber reacquisition adapter
  could run. This directly falsified the revision-1 intervention timing.
- The initial analyzer also treated ScienceWorld's returned valid-action list
  as an exhaustive native grammar. Native traces show accepted commands such as
  `focus`, `use`, and successful parameterized `move` actions that are absent
  from that list. The original metric output is retained; confirmation will
  instead audit adapter-added commands as supported when they are either exact
  successful-witness commands or accepted by the native environment.
- Four abstentions had been omitted by the revision-1 runner. This was detected
  before revision 2 and corrected: all subsequent denominators contain all 403
  pre-existing incidents, with abstention counted as no repair.

## 2026-09-09: development revision 2 frozen before execution

- Clobber and stale-validation repair moved from post-effect compensation to a
  pre-execution preservation guard. The diagnosed destructive call artifact is
  retained but wrapped and not executed when its effect guard is applicable,
  non-goal-satisfying, and destroys a live downstream predicate.
- A rely-gap adapter now concatenates the not-yet-executed successful witness
  prefix before the matching consumer. This retains every source call ID and
  witness digest in adapter metadata while exposing one adapter boundary.
- Role mismatch remains a witnessed consumer wrapper; healthy chains remain
  byte-for-byte unchanged at the call level.
- Static development produced 403/403 diagnoses and adapters, with 100%
  diagnosis exactness, locality, and healthy-control invariance before any
  revision-2 native outcome was inspected. The method SHA-256 is
  `ee94eeb96b3b109856b1e61a50917a4be83eb9f81d53a9ac42eba811590d7ac5`.
- Revision 2 is the second of at most three registered mechanism revisions.

## 2026-09-09: LLM comparator schema correction before method lock

- The first LLM-comparator attempt used the Revision-1 action schema: it allowed
  only one witness call for a rely gap and proposed post-effect compensation for
  clobber conflicts. Revision 2 gave CGBAS a full ordered witness-prefix operation
  and a pre-execution preservation guard, so continuing to present the old schema
  as a matched comparator would be unfair.
- The complete first Qwen run, complete first Phi generation, partial first Phi
  native replay (161 records), and partial first Mistral generation (284 records)
  remain under `results/development/llm_adapters/`. They are excluded from the
  primary comparator selection, not deleted or relabeled.
- Before any confirmation roster or outcome existed, the LLM schema was revised
  to expose exactly the same four operation types as Revision 2: no-op, ordered
  witness-prefix insertion, witnessed consumer replacement, and preservation
  guard. Model outputs may select only existing source/candidate call IDs; invalid
  selections or abstentions execute the unchanged candidate and count as failure.
- Qwen3-4B, Phi-4-mini, and Mistral-7B use revision-pinned weights, greedy
  decoding, identical public incidents and prompts, and the same native executor.

## 2026-09-09: development gate passed and method frozen

- All seven development arms contain 403 native replays with no technical
  errors and matched initial states. The causal denominator is 256 diagnosed
  conflicts; 147 healthy chains are controls.
- Constrained causal repair success is 100.0% for CGBAS, 0.0% for no repair,
  9.77% for the pairwise contract heuristic, 35.16% for Qwen3-4B, 46.48% for
  Phi-4-mini, and 51.56% for Mistral-7B. Whole-chain rollback reaches 100.0%
  ordinary native success but 0.0% constrained local success because it replaces
  the complete chain.
- The predeclared selection rule therefore freezes Mistral-7B as the strongest
  deployable local comparator. CGBAS exceeds it by 48.44 percentage points on
  exposed development evidence, with zero healthy-control loss and 100% command
  support. All development gates pass.
- CGBAS inserts one adapter call, but this is not always a low action cost. Across
  all development incidents it proposes 3.81 adapter actions on average; rely-gap
  adapters average 16.49 actions and reach a maximum of 66. These costs will be
  reported alongside success and locality.
- `research/CONFIRMATION_METHOD_LOCK.json` freezes method revision 2, the Mistral
  comparator, endpoint, gates, prompts, model revisions, runners, analysis code,
  external environment code, and ScienceWorld JAR before roster selection.
- The content-blind confirmation roster then selected 74 unique tasks (40
  ALFWorld and 34 ScienceWorld), with zero identifier overlap against the union
  of 2,498 task identifiers exposed by Papers 01--12 or Paper 13 development.

## 2026-09-09: independent confirmation completed

- Three unsuccessful source tasks were retained and not replaced. The 71
  successful sources yielded 349 planned incidents. State-matched causal replay
  completed all 627 candidate/correction executions with no technical errors or
  initial-state mismatches.
- The common frozen validity rule retained 226 causal conflicts and 71 healthy
  controls and excluded 52 non-causal clobber/stale mutations. Valid causal
  counts were 71 rely gaps, 71 role mismatches, 42 clobbers, and 42 stale
  validations; no excluded incident was relabeled or replaced.
- All seven frozen program arms completed 349 native executions with exit code
  zero. CGBAS reached 100.0% constrained causal success; the frozen Mistral-7B
  comparator reached 49.56%, Phi-4-mini 42.92%, Qwen3-4B 36.73%, pairwise
  contract 7.52%, and no repair 0%. Whole-chain rollback reached 100.0% ordinary
  success but 0% constrained success because it violated call locality.
- The primary paired gain was 50.44 percentage points. The 10,000-replicate
  family/environment-stratified task-cluster bootstrap interval was
  [46.61, 54.59] points, and the two-sided 100,000-replicate task sign
  randomization test gave `p=0.00001`. Healthy-control loss was zero.
- Every one of the 17 frozen confirmation checks passed. CGBAS had complete
  locality, provenance, adapter-command support, and initial-state matching with
  no technical errors. It proposed 7.14 adapter actions per causal incident on
  average; rely-gap adapters averaged 18.89 and reached 110 actions, so the
  result is a call-locality claim rather than a constant-cost claim.
