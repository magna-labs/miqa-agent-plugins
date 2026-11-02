---
name: version-compare
description: Use when the user wants to compare any two versions or builds of a Miqa test chain, e.g. "compare run 1234 with 1240", "what is different between the 21 Oct and 26 Oct builds", "did these two builds give the same results", "diff these two versions and show me" (via a connected Miqa MCP server). Compares the code side (version, components, trigger commit) with diff_test_chain_runs and the results side (metric values and check outcomes) from the metric history and run results, says what differs in each, and offers a private page for sharing. Read-only. Not for finding where a metric moved (use regression-bisect) or one build's results (use version-rollup).
metadata:
  summary: Compare two builds of a test chain: what differs in the code and in the results.
  version: 0.1.0
---

# Version Compare

Put two versions of one test chain side by side: what differs in the code, and what differs in the results. The two
halves are separate evidence. The diff says what changed in the build, the metric history says what changed in the
output. Say which is which, and never connect them with a cause you have not seen.

## Tools

Tool names follow `mcp__<server>__<tool>`. Used here: `list_test_chain_runs_for_trigger` or
`find_test_chain_runs_by_chain_name` (to turn builds into run ids), `diff_test_chain_runs`, `get_all_metrics` (with
`summary=true` when the deployment has it), `get_test_chain_run_results`. Call `get_org_context` first. On a hosted
server `set_organization` is unavailable, so do not claim which organization the data came from unless a tool said so.

## Procedure

1. **Resolve the two versions.** The user gives run ids, or builds by docker tag or date. Resolve builds to run ids,
   newest run per build. Both runs must be of the same test chain; if not, say so and stop, since the results side only
   compares one chain.
2. **Code side.** `diff_test_chain_runs(run_a, run_b)`. Report the changed fields, changed components and the trigger
   commit. It compares version, components and commit only. It does not compare datasets or outputs, so say that.
   Note image details that matter to the reading (a snapshot repository against a release repository, a different
   workflow version) as facts.
3. **Results side.** `get_all_metrics` with `tc_ids` for the chain, `metric_category=test_assertion`, `summary=true`,
   `version_field=docker_tag`, and a `limit` wide enough to include both builds (widen if either is missing; the window
   is counted in versions pipeline-wide). For each metric and dataset, take the value at version A and at version B.
   Keep metrics whose value differs. Report the before and after values and the signed difference in the metric's own
   units, never in multiples of a smallest unit. Values stored to four decimals cannot show smaller changes; say so when
   a difference is one last digit.
4. **Outcomes.** `get_test_chain_run_results` for both runs. Count `check_status` for each, and list checks whose status
   differs, with the direction. `assertion_status` can differ from `check_status`; say which you count.
5. **Is it the same?** If no metric differs and no outcome differs, say the results are identical at the stored
   precision. Say the same for the code side only if `identical` is true in the diff.
6. **Terminal summary first:** the code differences, the count of metrics that differ, the largest differences with
   before and after, the outcome changes, and what could not be compared.
7. **Offer once** a private page. Layout: the two versions named with run ids and dates, a code-differences block, a
   results table (metric, dataset, version A, version B, difference), outcome changes, and sources with the read date. Put
   caveats in a short note beside what they qualify (the precision of the values, which status was counted, what the
   diff does not compare), not in a section of their own. Use real sample names for the team and anonymize only if the
   user says the page goes outside. Say a published page is private until the user shares it.

## Never

- change, rebaseline or retry anything. This skill is read-only;
- name a cause for a difference, or say a change is expected unless told;
- present a difference as a multiple of a unit (for example "−3") instead of the real values;
- say two versions are identical on any side you did not compare;
- compare runs from different test chains.
