# Literature boundary

## Corpus basis

The topic was selected from the 255-paper Agent Skill lifecycle corpus under
`/mnt/disk2/work/机器人3875/autodl_inputs/01_agent_skill_lifecycle`. The closest
stored papers cover composition selection, graph execution, failure diagnosis,
local repair, and lifecycle history. Their abstracts and the retained Paper 06
evidence define the following boundary.

## Closest work

| Work | What it already provides | Remaining distinction |
|---|---|---|
| Generative Skill Composition | Joint selection of Skill subset, count, and order | Chooses a composition; does not repair a diagnosed interface while preserving component identities |
| GraSP | Typed DAG composition, node verification, and local repair | Optimizes end-task orchestration; does not isolate the value of a minimal witness-backed boundary adapter against whole-chain replacement |
| SkillHone | Persistent histories of diagnoses, revisions, evidence, and rejected alternatives | Maintains evolution history; does not compile that history into executable cross-Skill adapters |
| SkillAudit | Paired trajectory auditing for evolution | Audits candidate revisions; does not synthesize an interface mediator for a fixed composition |
| SkillCoach | Process rubrics for selection, following, composition, and reflection | Scores execution quality; does not provide an executable repair with a locality invariant |
| SkillOps | Typed lifecycle management and compatibility diagnosis | Supplies broad management motivation rather than a causal native boundary-repair evaluation |
| Paper 06 / MRGD | Exact pre-execution conflict class and minimal boundary diagnosis | Explicitly does not retrieve, reorder, execute, or repair Skills |

## Gap and non-overlap

After a composition checker identifies an incompatible boundary, maintainers
still face a deployment choice: rewrite a previously validated Skill, replace
the whole chain, reject the task, or mediate the boundary. Rewriting broadens
the regression surface; whole-chain rollback discards unrelated changes; and
rejection loses capability. The missing narrow question is whether successful
provenance witnesses and typed rely/guarantee clauses are sufficient to compile
a small executable adapter that restores the handoff while leaving component
Skill artifacts unchanged.

Paper 06 is diagnosis. Paper 13 is intervention. It uses Paper 06 confirmation
records only as exposed development evidence, measures repaired native success
and locality rather than diagnostic F1, and requires a new zero-overlap
confirmation cohort before making an effectiveness claim.
