---
name: release-dossier
description: Use when the user wants a release or build verification summary for other people to read, e.g. "release sign-off for build X", "is this candidate ready", "verification summary for the release", "what ran on the latest release candidate and what needs a decision" (via a connected Miqa MCP server). Resolves the candidate build, tallies every chain's checks, says for each warning or failure whether it is new in this build or has been there for a while, and lists what was tested for traceability. Terminal summary first, then a private HTML dossier on request. Differs from version-rollup (a terminal tally with no history) by adding the since-when and the traceability. Read-only. Makes no compliance claim.
metadata:
  summary: A release verification summary: what ran, what is new, what needs a decision.
  version: 0.1.0
---

# Release Dossier

A traceable "what was tested, against what, with what result, and what is new" for one build. Nothing about any
particular pipeline belongs in this file.

## Tools

Tool names follow `mcp__<server>__<tool>`, and the gateway tools may carry an `api_` prefix. Use
`list_test_chain_runs`, `find_test_chain_runs_by_version`, `get_test_chain_run_results`,
`list_component_versions_for_test_chain_run`, `get_test_chain_run_report` and `get_all_metrics` (with `summary=true`
when the deployment has it). `get_test_chain_run` can fail on some deployments with an output validation error:
use the results and report tools instead. Call `get_org_context` first; on a hosted server `set_organization` is
unavailable, so do not claim which organization the data came from unless a tool told you.

## Procedure

1. **Resolve the candidate.** From a docker tag or version label, use `find_test_chain_runs_by_version` or scan
   `list_test_chain_runs` (a limit of about 100 covers recent builds). Runs of one build usually span all the release
   chains within a short window. Use the newest run per chain for that build, and list any release chain with no run
   for it as "not run". Find the comparison build the same way: the previous build on the same release line, same
   chains.
2. **Tally.** `get_test_chain_run_results(run_id)` once per run: it covers every sample. Count by `check_status`
   (PASS, WARN, FAIL, INCOMPLETE); `check_status` is what the run report shows. `assertion_status` can be FAIL while
   its `check_status` is PASS, so say which one you count. If checks are INCOMPLETE with an output-folder error, the
   execution itself likely failed: look at `get_test_chain_run_environment` before treating each as separate.
3. **Verdict.** Any failed chain or FAIL check: "Not ready for sign-off". Otherwise warnings that need a decision, or
   "No failing checks". Say what the verdict is based on (the checks counted, the comparison build).
4. **Since when.** For every warning and failure, ask `get_all_metrics` with `summary=true` for that chain's series and
   say whether its outcome or value stepped at this build (new), at an earlier build (since then, name it), or never
   (long-standing). Do not call a long-standing item a regression. Assertions with `failtype: warn` surface as WARN
   checks, and a check that compares with the previous version fails once at a step and then passes by itself, so a
   passing latest result can hide a recent step.
5. **Traceability.** For each chain: run id, component versions
   (`list_component_versions_for_test_chain_run`), and the trigger repo and commit from the `metadata` block of
   `get_test_chain_run_report`. For a failing or warning check that needs explaining, read the report narrowed to that
   check name; it is large. Tables of failing variants or records are not available through the connector (only a
   link into the web app), so say so instead of guessing at their contents.
6. **Report in the terminal first:** verdict, totals, a per-chain table (outcome, pass/warn/fail counts, comparison
   build outcome, run id), a "needs a decision" list with since-when, and what was not run.

## Optional private page

Offer it once. When asked, publish a private artifact: verdict banner, totals, per-chain table with a stacked
pass/warn/fail bar, the needs-a-decision list, and a what-was-tested table. Anonymize on request (generic pipeline
names, no registry paths or commit hashes) and keep run ids as plain text without links. Say that it is private and that
others cannot open it until it is shared. State in the page that it records what was measured and makes no claim about
regulatory or audit status. Do not publish without a yes.

## Never

- say compliant, validated or audit-ready;
- change, rebaseline or retry anything. This skill is read-only;
- present a missing run as passing.
