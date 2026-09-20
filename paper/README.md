# Manuscript build

`en/main.tex` is the canonical English manuscript. `zh/main.tex` is the complete
Chinese counterpart, not a machine-generated abstract. Both consume the same
result macros generated from `results/confirmation/final/summary.json`.

To regenerate the tables and build both manuscripts:

```bash
python3 scripts/render_paper_assets.py
bash paper/build.sh
```

The build requires XeLaTeX, `latexmk`, and Noto Serif/Sans CJK SC for the Chinese
PDF. Tables and numeric macros are generated artifacts; do not manually change a
reported value without changing and rerunning its source analysis.

The released PDFs report the passed independent confirmation: 226 causal
conflicts and 71 controls, with a 50.4-point paired gain over the frozen
Mistral-7B comparator (95% task-clustered CI 46.6--54.6).

Before submission, complete `STATEMENTS_AND_DECLARATIONS.md`, replace anonymous
author metadata, add the repository URL or DOI, and format the journal-neutral
source for the selected journal. The English title and abstract are canonical.
