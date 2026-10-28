---
name: coverage-audit
description: Use when the user asks what Miqa is and is not testing, e.g. "which triggers are stale or never ran", "does every pipeline have a timing check", "which test blocks can never fail a run", "what are we not covering", "audit our test setup" (via a connected Miqa MCP server). Lists triggers by state, reads each active test block's current assertions, and reports gaps: no run-time check, no comparison with a previous or baseline version, every check set to warn, thresholds the data has never met. Read-only. Reports observations about configuration; it does not add or change checks.
metadata:
  summary: Map what your tests would and would not catch: stale triggers, missing checks, checks that cannot fail.
  version: 0.1.0
---

# Coverage Audit

A map of what the configured tests would and would not catch. It describes the configuration and what the history shows.
Whether a gap matters is the owner's call. Nothing about any particular pipeline belongs in this file.

## Tools

Tool names follow `mcp__<server>__<tool>`, and the gateway tools may carry an `api_` prefix: `list_test_triggers`,
`list_test_chain_runs_for_trigger`, `get_test_blocks`, `get_test_block_versions`, `get_test_block_version`,
`get_all_metrics` (with `summary=true` when the deployment has it). Call `get_org_context` first; on a hosted server
`set_organization` is unavailable, so do not claim which organization the data came from unless a tool told you.

## Procedure

1. **Triggers by state.** `list_test_triggers` returns id, name, `disabled` and `last_run_date`. Trigger names are not
   unique, so identify by id. Count and group: active and recent, disabled, never run (`last_run_date` null), and
   stale (no run for a window the user can change, 90 days by default). Report counts and a short list of each group,
   not a table of every trigger. Names such as "archive" or "deprecated" are hints, not facts: say so.
2. **Pick the scope.** Ask which active triggers or chains to audit if there are many; default to the triggers that
   ran recently. `list_test_chain_runs_for_trigger` gives a trigger's chain.
3. **Read the checks.** `get_test_blocks(q=...)` finds blocks by name. `get_test_block_versions(tb_id)` lists
   versions: use the one flagged current, not the newest by number. `get_test_block_version(version_id)` returns the
   assertions JSON: check groups keyed by type, each check with its `failtype`, thresholds and comparison settings.
   Read it for structure only; do not paste whole blobs.
4. **Classify each current block** on these dimensions, from the assertion JSON:
   - **Run time**: is there a timing check? A pipeline whose run time moved with no check noticing is the usual finding.
   - **Comparison with an earlier version**: `versions: [-1]` compares with the previous version, `versions:
     ["@release_series"]` compares with a baseline picked from the same release series (so builds of different
     release lines are not compared with each other), and a check with neither is an absolute check or a display.
     Say which, since a comparison with a previous version fails once at a step and then passes by itself. Always
     read the block's current version: older versions can use a different comparison.
   - **Absolute floors**: static thresholds on metrics, and the `failtype` of each. `relationship` is the failing
     condition (`lt` with `static` 0.9786 fails when the value is below 0.9786), so a name like "X >= 0.9786" and
     `lt` agree.
   - **Display checks that warn by construction**: a check whose failing condition is always true (for example
     `relationship: ge` with `static: 0` on a count) shows a table and always warns. It is not a signal; say so.
   - **Change tolerances**: for "change vs previous <= N%" checks, compare N with the size of the steps the history
     actually shows. A step smaller than N passes.
   - **Requirement tracing**: whether checks carry requirement or test-case IDs (extra fields such as `TRQ ID`). Report
     which blocks do and which do not, without judging.
   - **Hard failure**: whether any check has `failtype` fail. A block whose checks are all warn can never fail a run.
   - **File presence**: a file-count or file-collection check.
5. **Check thresholds against history.** For floor checks, `get_all_metrics` with `summary=true` shows each value's
   plateaus. Say when a metric has sat on the wrong side of its threshold for every build in the window (a check that
   has always warned), or sits within a hair of it (a margin of one last digit).
6. **Report** a matrix, one row per block: run-time check, comparison type, floors, can it fail a run, checks that always
   warn. Under it, a short "gaps" list with the evidence for each. Offer options without choosing: add a timing check,
   convert a warn to fail, move a floor, retire a stale trigger. The owner decides.

## Never

- change, create or disable anything. This skill is read-only;
- call a gap a defect, or recommend a threshold value;
- treat a trigger's name as proof that it is retired.
