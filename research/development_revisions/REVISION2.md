# Development revision 2 method lock

This revision was specified after revision 1 completed on exposed development
evidence and before any revision-2 native outcome was inspected.

## Mechanism changes

1. A terminal or otherwise destructive call cannot be repaired after it fires.
   CGBAS therefore replaces that call at execution time with a zero-action
   preservation wrapper when the diagnosed clobber is applicable,
   non-goal-satisfying, and live downstream.
2. A missing rely clause may stand for an omitted multi-call task prefix. CGBAS
   takes the consumer's immutable source call ID, locates it in the successful
   witness chain, and joins only the witness calls before that consumer that are
   absent from the current prefix. The joined fragment is one adapter with all
   source IDs and witness digests retained.
3. Every exposed incident remains in the native denominator. Synthesis
   abstention executes the unchanged candidate and counts as repair failure.

## Command-support audit

ScienceWorld's returned valid-action list is not exhaustive for parameterized
commands. A command added by an adapter passes the support audit only when it is
an exact command from the linked successful witness or when the native
environment accepts the generated command. Counts for all original component
commands are reported separately and do not change constrained repair success.

## Frozen development files

- `src/cgba/adapters.py`: `ee94eeb96b3b109856b1e61a50917a4be83eb9f81d53a9ac42eba811590d7ac5`
- `results/development/static/adapters.jsonl`: `3d7cd911d7eb1458fe45b96d04fe92c27900113f14458e0efcdb3df8664bed9a`
- Development incidents: 403; synthesized: 403; abstained: 0.

The third and final development revision remains unused.
