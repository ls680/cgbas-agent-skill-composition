# Corpus-grounded topic evidence

## Source snapshot

Paper 13 was selected from the user-provided Agent Skill lifecycle corpus at
`/mnt/disk2/work/机器人3875/autodl_inputs/01_agent_skill_lifecycle`. The topic
decision used metadata and abstracts, not inferred full-text claims.

| Corpus artifact | SHA-256 |
|---|---|
| `core_papers.parquet` | `65661dc4b33e9d312b8d4a04d94db0f3761ebc47f898de99807bd5d8a0c853ef` |
| `paper_ranking.csv` | `56ba7445666df8463b87d3d8d7273c58b977ed9288478d8aa9d2e54443d6292d` |
| `seed_papers.md` | `1bc5e36173d0b1d4a10d48cd601ddacac3acc7919866392f7b5697097d6f7af9` |

## Evidence used to define the contribution

| Corpus paper | Abstract-backed contribution | Consequence for Paper 13 |
|---|---|---|
| Generative Skill Composition for LLM Agents (Zhao et al., 2026; arXiv:2606.32025) | Jointly predicts the selected subset, number, and order of Skills | Hold selection fixed and study post-diagnosis interface repair |
| GraSP: Graph-Structured Skill Compositions for LLM Agents (Xia et al., 2026; arXiv:2604.17870) | Compiles Skills into typed DAGs with node verification and locality-bounded repair | Isolate one repair mechanism and causally compare it with rollback and local baselines |
| SkillOps (Pu et al., 2026; arXiv:2605.13716) | Represents library artifacts with typed contracts and diagnoses compatibility debt | Compile rely/guarantee and liveness evidence into an executable adapter rather than only a health report |
| SkillTrace: Multi-Trace Provenance Auditing (Chen et al., 2026; arXiv:2608.05204) | Attributes Skill reuse through expression, implementation, and operational traces | Require every generated command or role mapping to retain successful provenance |
| SkillHone (Li and Hu, 2026; arXiv:2606.08671) | Persists diagnoses, revisions, evidence, and rejected alternatives across evolution sessions | Preserve the failed first repair and freeze the successful revision history |
| SkillAudit (Gao et al., 2026; arXiv:2606.14239) | Uses paired trajectories and rolls back harmful updates without hidden outcome access during evolution | Use state-matched candidate/correction runs and keep confirmation outcomes sealed until programs are frozen |
| SkillCoach (Zhu et al., 2026; arXiv:2607.01874) | Separates process quality from final verifier success | Report locality, command support, provenance, and cost in addition to native success |
| SkillFuzz (Hu et al., 2026; arXiv:2607.02345) | Uses extracted contracts to prioritize composition interactions before execution | Treat the composition boundary, rather than an isolated Skill, as the unit under intervention |

## Narrow research gap

The corpus already contains methods for selecting a Skill chain, compiling a
graph, diagnosing compatibility, auditing provenance, and evolving whole Skill
artifacts. The remaining testable question is narrower: after a particular
boundary has been diagnosed, can retained successful provenance be compiled into
one executable boundary adapter that restores native success while leaving the
component Skill artifacts unchanged? Paper 13 evaluates that question and does
not claim a new general planner, retriever, or whole-Skill evolution system.
