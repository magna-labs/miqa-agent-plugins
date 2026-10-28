---
name: weekly-report
description: Use when the user wants the weekly verification report across their active Miqa test triggers, e.g. "weekly report", "what happened this week", "weekly verification for the release pipelines", "which pipelines need attention" (via a connected Miqa MCP server). Pulls the active triggers, compares this week's builds with last week's, gives check-level detail for anything failing, says what is still running and how long a problem has been there, and ends with questions for the reviewer. Terminal first, then a private page on request. Read-only.
metadata:
  summary: The week's builds across your active triggers: what failed, what is new, what was already failing.
  version: 0.1.0
---

# Weekly Verification Report

The report a reviewer presents each week. It covers every active trigger, so it needs no list of pipelines from the
user. It defers to the sibling `active-triggers`, `version-rollup` and `metric-trends` skills for procedure and adds
the weekly framing. Call `get_org_context` first. On a hosted server `set_organization` is unavailable, so do not
claim which organization the data came from unless a tool said so.

## Scope

1. **Pull the active triggers.** Follow step 1 and 2 of `active-triggers`: `list_test_triggers`, keep `disabled: false`,
   then keep the triggers with a run in the last 14 days. Trigger names are not unique, so identify by id. Say how many
   triggers you left out as disabled or dormant, and name none of them unless asked.
2. **Window.** The last seven days unless the user asks otherwise, plus the previous week's build for comparison.
3. **Builds.** Docker tags usually look like `<version>-<yyMMdd>-<hash>`; take the tag after the last colon in
   `version_name`. Builds from a PR or branch carry a branch-style name; leave them out of a release report and say so.

## Procedure

1. **Runs.** `list_test_chain_runs_for_trigger` for each active trigger. Group by build tag and take the newest run per
   chain for each build. A chain with no run for a build is "not run". A run with `status: started` is still running,
   not failed. Durations that stop at the same round figure on several runs look like a time limit; say so as an
   observation.
2. **Status table.** Pipelines down, builds across: PASS, FAIL, RUNNING, not run.
3. **Detail for anything failing.** `get_test_chain_run_results(run_id)` once per run. Count by `check_status` and list
   the failing checks with the value and limit if present. `assertion_status` can read FAIL while `check_status` is
   PASS, so say which you count. Compare with the previous build's values: identical values across two builds mean the
   change is deterministic.
4. **Since when.** `get_all_metrics` for each failing chain (`summary=true` if the deployment has it): did the value
   step on this build, or earlier? Widen the window beyond 25 versions for a chain that ran in few of them.
5. **What changed.** If `diff_test_chain_runs` exists, diff the last passing run against the first failing one. If
   not, say what you could not compare. This is the code side only; do not connect it to the result with a cause.
6. **Questions for the reviewer.** End with what you cannot know: which changes are expected, which tolerances apply,
   and what the reviewer wants to headline.

## Output

Terminal first: the headline (which pipelines need attention), the status table, then one short block per failing or
running chain. Offer once a private page in this layout: headline banner, status table, needs-attention blocks with the
check values, and the reviewer questions. Use real pipeline names for the team, and anonymize if the user says the page
goes outside. Say that a published page is private until the user shares it.

## Never

- change, rebaseline or retry anything. This skill is read-only;
- name a cause you have not seen, or call a failure expected without being told. A result that was failing and now
  reads pass has changed in between; say so, and say you cannot see why;
- call a missing or still-running run a pass.
