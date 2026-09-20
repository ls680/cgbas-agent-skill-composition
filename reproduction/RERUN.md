# Reproduction workflow

## Verify the released result without GPU inference

Use Python 3.12.3. Install the local project and test dependency, then run:

```bash
python3 -m pip install -e '.[test]'
python3 reproduction/verify_method_lock.py
python3 -m pytest -q
bash reproduction/analyze_all.sh
bash paper/build.sh
```

This recomputes the frozen statistics and paper tables from released program and
native outcome records. It does not download model weights or datasets.

## Full native rerun on one RTX 3090

The experiment used one 24GB RTX 3090. Point `ALFWORLD_DATA` to a compatible
ALFWorld data tree and `HF_HOME` to a data-disk Hugging Face cache containing the
three exact revisions in `configs/models.json`. Provide the ScienceWorld JAR at
the path recorded in `configs/confirmation.json`, or update all dependency paths
in a new experimental copy and create a new lock before running. Do not modify a
released frozen result tree in place.

Install the pinned native and model dependencies with
`python3 -m pip install -e '.[test,native,llm]'`, then verify exact runtime
versions against `environment/runtime_manifest.json` before a full rerun.

The prospective execution order is:

```bash
python3 scripts/freeze_confirmation_roster.py
python3 scripts/collect_confirmation_oracles.py
python3 scripts/generate_confirmation_incidents.py
python3 scripts/build_confirmation_programs.py
python3 scripts/run_confirmation_llm_adapter.py --model-label qwen3_4b
python3 scripts/run_confirmation_llm_adapter.py --model-label phi4_mini
python3 scripts/run_confirmation_llm_adapter.py --model-label mistral7b_v03
python3 scripts/run_confirmation_causal_native.py
```

Then execute every file under `results/confirmation/programs/*/programs.jsonl`
with `scripts/run_confirmation_programs_native.py`, using an arm-specific output
directory under `results/confirmation/native/`. Finally run
`bash reproduction/analyze_all.sh`.

The confirmation scripts refuse changed run specifications and resume append-only
outputs by identifier. For a clean rerun, work in a separate extracted copy with
generated confirmation output directories absent; never delete the released
evidence to make room for a rerun.
