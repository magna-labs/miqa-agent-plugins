---
name: regression-bisect
description: Use when a Miqa metric, check outcome or run time moved and the user asks "which build changed this", "when did this start", "what changed between these runs", "bisect this regression", or wants a step in a metric history explained (via a connected Miqa MCP server). Finds the step with get_all_metrics summary mode, bounds it between the last normal and the first changed version, diffs those two runs with diff_test_chain_runs, checks whether other pipelines moved on the same builds, and reports evidence apart from inference. Read-only. Not for one build's results (use version-rollup) or a trigger's current health (use active-triggers).
metadata:
  summary: Find which build moved a metric, bound the change, and separate evidence from inference.
  version: 0.1.0
---

# Regression Bisect

Answers "where did this move, and what changed there". It describes what happened and what differed between two
runs. It does not name a cause it has not seen. Nothing about any particular pipeline belongs in this file.

## Tools and fallbacks

Tool names follow `mcp__<server>__<tool>`, and the gateway tools may carry an `api_` prefix.

- `get_all_metrics` with `summary=true`: one statistics row per metric and dataset instead of one cell per version.
  If the response still has one key per version, the deployment predates summary mode: pull raw rows with narrow
  filters, save the response to a file and compute the plateaus with code. Never read large raw responses by eye.
- `diff_test_chain_runs(run_a, run_b)`. If it is not available, fall back to
  `list_component_versions_for_test_chain_run` on both runs plus the `metadata` block of
  `get_test_chain_run_report` on both (component version, trigger repo and commit), and compare by hand.
- Call `get_org_context` before the first read. With several organizations and none selected, ask once.
  `set_organization` is unavailable on a hosted server; reads then use the caller's default organization, so do not
  claim which organization the data came from unless a tool told you.

## Procedure

1. **Scope.** Resolve the chain: `find_test_chain_runs_by_chain_name` returns each run's `testchain_id` and
   `version_name`. The `all_metrics` window counts versions across the whole pipeline, not per chain, so a chain that
   ran in few versions returns few rows. If fewer than about 10 versions have a value, widen the window in steps
   (25, then 100, then 0) and say so each time. Chains in different pipelines need separate calls: `tc_ids` spanning
   pipelines is a 400.
2. **Pull summaries.** `summary=true`, `version_field=docker_tag`, `tc_ids`, and one call per category:
   `metric_category=test_assertion`, and `metric_category=execution` with the chain's `ds_ids` for run time.
3. **Read the steps.** Each series carries `plateaus` (runs of identical values) and `steps` (`at` is the first
   version of the new value, with `from`, `to` and `delta` for numbers). Say which series are deterministic (a few
   plateaus, identical inside each) and which vary run to run. A step in a deterministic series is a real change. A
   step in a noisy series needs a band: state the one you used (for example median of the per-version medians plus or
   minus two robust standard deviations) and that it is your choice. Series that step at the same version are one
   event, so report them together.
4. **Bound it.** Last normal is the last version of the previous plateau, first changed is the step's `at`. If versions
   between them have no value (failed runs, missing results), the change is bounded but not pinpointed: name the
   window. Failed executions whose durations repeat one figure (about 43,200 s) look like a time limit, which is an
   inference, so say so.
5. **Map versions to runs.** A version label is `docker_tag (version id)`, or the bare id when the version has no
   docker tag; say that it then has no tag and no build date, and place it by order between its neighbours. The id in
   the label is not the run's `versionidentifier_id`: match runs to labels by the docker tag inside the run's
   `version_name`, and match an untagged version to the run whose name is a workflow name, confirming by date.
6. **Diff.** `diff_test_chain_runs(run_a=<last normal run>, run_b=<first changed run>)`. Evidence is a changed
   `component_info.docker_tag`, a changed `trigger.commit` or `trigger.repo`, and entries under `components.changed`,
   `only_in_a` and `only_in_b`. A different `version.name` on its own is not evidence: that name is a version
   identifier that may simply count builds. If nothing differs, say the diff found no difference in what it compares
   (versions, commit, trigger) and the cause may lie outside it (data, infrastructure, configuration).
7. **Cross-check other pipelines.** Repeat steps 2 to 4 for sibling chains and see whether they moved on the same
   builds. A coincidence across pipelines is worth reporting, as a coincidence only.
8. **Read outcomes correctly.** An assertion's `outcome` of fail is not a failing run: assertions with `failtype: warn`
   surface as WARN checks. A check configured to compare with the previous version (`versions: [-1]`) fails once at a
   step and passes afterwards without anyone rebaselining, so do not infer a rebaseline from it. Check
   `list_run_interventions_for_chain` (if the deployment has it) before saying anything about rebaselines or forced
   results.

## Report

First a table, one row per event: what moved, from and to, last normal build, first changed build, bounded or
pinpointed, diff evidence, other pipelines affected. Then three short lists: **Evidence**, **Inference**, **Not
known**. Then offer once a private chart (a run-over-build chart with the steps marked). Do not publish without a yes,
and say that others cannot open an artifact until it is shared.

## Never

- name a cause that is not in the diff, or treat a version identifier name as evidence;
- print object-valued rows, or read raw per-version responses by eye;
- change, rebaseline or retry anything. This skill is read-only.
