# Third-party components

The reproducibility bundle may contain result traces and project code, but it
must not silently relicense external datasets, environments, model weights, or
earlier paper artifacts.

- ALFWorld data and runtime: install or obtain under the upstream terms.
- ScienceWorld JAR: obtain under the upstream terms; the frozen experiment uses
  the SHA-256 recorded in `research/CONFIRMATION_METHOD_LOCK.json`.
- Qwen3-4B-Instruct-2507, Phi-4-mini-instruct, and Mistral-7B-Instruct-v0.3:
  obtain the exact revisions recorded in `configs/models.json` under their
  respective licenses.
- Paper 01 and Paper 06 local executors are experimental dependencies. Exact
  source snapshots needed by Paper 13 are retained under `reproduction/vendor/`;
  `vendor_manifest.json` records their hashes and `prepare_workspace.sh` restores
  the sibling layout expected by the frozen scripts.

No model weights, Hugging Face cache, ALFWorld dataset copy, or environment
container image should be added to the GitHub repository or source archive.
