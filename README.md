# Contract-Guided Boundary Adapter Synthesis

This directory contains Paper 13 in the Agent Skill lifecycle research matrix.

Working title: **Repair the Boundary, Not the Skills: Contract-Guided Adapter
Synthesis for LLM-Agent Skill Composition**.

Public repository: https://github.com/ls680/cgbas-agent-skill-composition

The versioned reproducibility archive is linked to the repository through the
Zenodo record listed in the release metadata after publication.

The study asks whether an already diagnosed cross-Skill interface conflict can
be repaired by a witness-backed boundary adapter without rewriting the
component Skills. Paper 06 supplies exposed development evidence only. Paper 13
then freezes the method, baselines, endpoint, and analysis before selecting a
74-task, identifier-disjoint confirmation roster.

The independent confirmation gate passed on 2026-09-09. State-matched replay
retained 226 causal conflicts and 71 healthy controls. CGBAS achieved 100.0%
constrained native repair success versus 49.6% for the frozen strongest local
comparator, a 50.4-point gain (95% task-clustered bootstrap CI 46.6--54.6;
two-sided task sign-randomization `p=0.00001`) with zero healthy-control loss.
The claim remains limited to controlled interface regressions with a correct
diagnosis and current successful provenance.

## Layout

- `research/`: literature boundary, protocol, decisions, and audit trail
- `src/cgba/`: diagnosis and boundary-adapter implementation
- `scripts/`: development, native replay, confirmation, and release tooling
- `data/`: generated development and sealed confirmation inputs
- `results/`: append-only native traces and analyses
- `paper/`: English and Chinese manuscripts
- `reproduction/`: standalone replay workflow and vendored adapters
- `artifacts/`: checksummed submission and reproducibility packages

## Verify

```bash
python3 reproduction/verify_method_lock.py
python3 -m pytest -q
python3 scripts/analyze_confirmation.py
python3 scripts/render_paper_assets.py
bash paper/build.sh
python3 scripts/verify_release.py
```
