---
name: assertion-lint
description: Use when the user asks to lint, review, sanity-check or tidy a Miqa Test Block or a set of assertions, e.g. "lint this test block", "what's wrong with these assertions", "why does this check never fail", "can this block be faster", "find the mistakes in this check", or pastes assertions JSON and asks whether it is correct (via a connected Miqa MCP server). Reads the assertions, finds structural errors, checks that each check can actually pass and fail the way its name says, flags names used in the wrong place, and suggests reuse and performance improvements. Report-only: it never edits, saves or publishes a Test Block.
metadata:
  summary: Lint a Test Block's assertions for errors, unclear pass/fail, and reuse or performance problems.
  version: 0.1.0
---

# Assertion lint

Reads a Test Block's `assertions` and reports what is wrong, what cannot work the way it reads, and
what could be simpler or faster. It does not change anything. It proposes fixes as small JSON edits
and leaves applying them to the user.

It calls `get_output_explorer_vocabulary`, `api_get_test_blocks`, `api_get_test_block_version` and,
when a proof is wanted, `api_run_adhoc_assertions` on whichever Miqa MCP server is connected (tool
names follow `mcp__<server-name>__<tool>`). It never calls a tool that writes or publishes.

## Procedure

1. **Get the assertions.** Use pasted JSON as it is. For a named Test Block, resolve it with
   `api_get_test_blocks(q=<name>)` (show id and name pairs if more than one matches; do not guess),
   then read the current version with `api_get_test_block_version`. If the JSON does not parse, say
   where it breaks and stop.

2. **Ground the rules.** Read `references/rules.md` in this skill's folder, and call
   `get_output_explorer_vocabulary()` once, at the same time. The vocabulary confirms which check
   types exist. Its field list is not exhaustive and allows extra keys, so use the seed list of known
   keys in `rules.md` to decide whether a key is wrong. A key that is neither known nor close to a
   known one is not an error: say you could not confirm it.

3. **Run the rules in order, and keep each finding separate.**
   1. **Errors** (rules `S*`). These are certain from the text alone: a key that is ignored, a
      variable that is not read, a table that is never shown.
   2. **Pass and fail** (rules `P*`). Work out when each check fails, and say it in plain words.
      Compare that with the check's `name` and `expected_result`.
   3. **Names in the wrong place** (rules `N*`).
   4. **Reuse and performance** (rules `R*`).
   5. **Hygiene** (rules `H*`).

4. **Be honest about confidence.** Mark each finding **error**, **likely mistake** or
   **suggestion**, using the severity in the rule. Lower a finding by one level when it rests on
   reading a name or title instead of on the structure of the check. When the text does not say what
   the author meant, say you cannot tell, and ask.

5. **Use measurements when there are any.** Performance findings depend on how many samples there
   are and how large the files are. Look for a run of the block's test chain with
   `list_test_chain_runs` (or `find_test_chain_runs_by_chain_name`), read the sample count from
   `get_test_chain_run` or `get_test_chain_run_results`, and the output files from
   `inspect_execution_outputs`. If no run is available, or a size is not available, ask the user for
   rough numbers. Label each performance finding **measured** or **assumed**.

6. **Prove a rewrite before recommending it.** For a suggestion that changes how a check is
   written (moving an expression into a variable, replacing per-sample tables with an aggregate
   table), run the original and the rewrite with `api_run_adhoc_assertions` on one execution and
   confirm they give the same result. If no run is possible, say the rewrite is untested. Findings
   from rules `S*` need no run. For a per-sample to aggregate table change, use the
   `table-config-to-aggregate` skill if it is installed, and otherwise describe the change.

7. **Report.** Give the findings grouped as errors, likely mistakes and suggestions. For each one:
   the check's position (its group and number, with the first few words of its name, since names
   are long and sometimes repeated), the key path, what is wrong in one sentence, why it matters, and
   the smallest edit that fixes it. Finish with what you could not check. Offer to apply the fixes as a new
   Test Block version only if the user asks.

## Things to watch

- A large version result may arrive truncated or be saved to a file. Parse the file with
  `python3 -I` or `jq` instead of reading it whole, and say if you could not read all of it.

- `relationship` is the condition under which a check **fails** in almost every check type. In
  `file_counts` it is the **pass** condition. Get the direction right before you flag one.
- A placeholder `stat` with `static: 0` and `relationship: "lt"` is normal on a check with
  `aggregate_check_only`. Do not flag it there.
- Do not flag a per-sample `table_config` beside an aggregate table when it is `download_only`.
  That is a common and good arrangement.
