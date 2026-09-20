# Development protocol: Contract-Guided Boundary Adapters

Recorded on 2026-09-09 before any Paper 13 native repair outcome was produced.

## Research question

When individually witnessed Agent Skills fail only at a diagnosed composition
boundary, can a witness-backed adapter restore native task success without
rewriting the component Skills or replacing the whole chain?

## Unit and intervention

The unit is a state-matched composition incident with a successful pre-change
witness, a failing candidate chain, and an MRGD diagnosis. Four conflict
classes are in scope: missing rely, role mismatch, live-state clobber, and stale
validation. Healthy chains are negative controls.

Contract-Guided Boundary Adapter Synthesis (CGBAS) performs one local operation:

1. insert a witnessed producer fragment that establishes a missing rely;
2. insert a role-mapping wrapper that specializes the consumer to the live
   producer binding and public objective;
3. insert a compensating reacquisition wrapper after a witnessed clobber; or
4. restore the clobbered predicate and repeat the invalidated check.

The original calls, call identifiers, and contracts are immutable. Inserted
wrappers record their diagnosis clause, source witness, and changed boundary.
The synthesizer may read public objective text, the candidate calls, MRGD
output, and provenance-linked successful calls. It may not read candidate or
adapter native outcomes, matched-correction programs, hidden task labels, or a
target expert plan.

## Development evidence

Paper 06's completed confirmation set is now exposed and is used only for
development. Its causal labels remain useful because each positive has a
successful source witness, a state-matched candidate failure, and an independently
executed one-boundary correction. Paper 13 does not reuse these tasks for
confirmation and does not claim them as new evidence.

## Comparators planned before confirmation

- no repair / reject after diagnosis;
- a contract-only local heuristic without provenance or liveness;
- whole-chain rollback to the last successful version;
- three revision-pinned local instruction models given the identical public
  incident, diagnosis, witness catalog, and output schema; and
- the matched correction as a labeled upper bound only, never a deployable
  comparator.

The strongest deployable development comparator by constrained native success
is frozen before confirmation.

## Endpoints

The primary endpoint is **constrained native repair success**: the environment
task succeeds, no original call artifact is edited, all executed environment
actions are native, and changes are confined to the diagnosed boundary plus at
most one inserted adapter call. Secondary outcomes are ordinary native success,
healthy-control non-regression, restored contract clauses, modified call count,
adapter action count, invalid action rate, token/runtime cost, and success by
conflict class and environment.

Inference clusters all arms and model variants by source task. Confirmation
uses a family/environment-stratified task bootstrap and a paired task sign
randomization test. Model outputs are repeated measurements, not independent
tasks.

## Development gate and revision budget

At most three mechanism revisions are allowed before confirmation. Development
advances only if all conditions hold on exposed evidence:

- at least 180 valid causal conflicts and 60 healthy controls;
- constrained native repair success at least 0.75;
- at least 15 percentage points over the strongest deployable comparator;
- positive repair gain in every conflict class and both environments represented;
- healthy-control success loss no more than 2 percentage points;
- at least 95% of repaired executions contain no invalid native action; and
- every inserted action or role mapping cites a witnessed clause or current
  native observation.

Failure after three revisions stops this paper and moves to another matrix cell.

## Independent confirmation if authorized

Confirmation uses at least 60 untouched tasks with zero identifier overlap
against Papers 01--12, balanced across available ALFWorld and ScienceWorld
families. The roster is selected by a fixed salted hash before collecting
source outcomes. Conflict specifications are generated before mutation
outcomes, and every causal label again requires source success, candidate
failure, matched-correction success, matched initial state, and no technical
error.

The positive gate requires at least 180 causal conflicts and 60 controls,
primary success at least 0.75, a gain of at least 15 points over the frozen
comparator, a 95% task-cluster interval above zero, paired randomization
`p<=0.01`, positive gain in both environments and all four conflict classes,
control non-regression within 2 points, no component-Skill edits, and complete
input/native/provenance audits.

## Claim boundary

The design evaluates controlled interface regressions in text-simulator Skill
programs with retained successful provenance. It does not show that arbitrary
production failures have these four causes, that a witness is current under
environment drift, or that local repair is always preferable to replanning.

## Prospective confirmation amendment (2026-09-09)

This amendment was recorded after Development Revision 2 but before the
confirmation roster was selected and before any confirmation source, mutation,
repair, or comparator outcome was observed.

- The fixed confirmation allocation is 74 untouched tasks: 40 ALFWorld tasks
  balanced across five eligible families and all 34 eligible untouched
  ScienceWorld use-thermometer tasks. This provides attrition margin above the
  unchanged minimum gates.
- For the primary endpoint, an adapter-added command is supported when it is an
  exact command from retained successful provenance or is accepted by the native
  environment. Rejected exploratory commands already present in an immutable
  component Skill are reported, but do not retroactively invalidate an otherwise
  supported adapter. This operationalizes the original native-action and
  provenance requirements for ScienceWorld, whose returned action list is not
  exhaustive.
- Positive per-class and per-environment repair gain is measured against no
  repair. The overall 15-point superiority gate remains relative to the strongest
  frozen deployable local comparator.
