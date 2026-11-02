---
name: requirements-coverage
description: Use when the user has a list of requirements and wants to know which of them the Miqa tests cover, e.g. "which of these requirements have a check", "map our requirements to the test blocks", "requirements coverage for this pipeline", "do we test everything in this spec", "trace these requirements to checks" (via a connected Miqa MCP server). Takes the requirements as a paste, a file or a ticket list, reads the current checks of the relevant test blocks, and maps each requirement to the checks that address it as covered, partly covered, not covered or not testable by a check, with the check as evidence. Offers a drafted check for each gap. Read-only until the user confirms a write. Makes no compliance claim. Differs from coverage-audit, which starts from the configuration and has no requirements list.
metadata:
  summary: Map a list of requirements to the checks that cover them, and show the gaps.
  version: 0.1.0
---

# Requirements Coverage

For each requirement in the user's list, say which checks address it and how well. It describes what the checks do. It
does not say a requirement is met, and whether a gap matters is the owner's call. Nothing about any particular
pipeline belongs in this file.

## Tools

Tool names follow `mcp__<server>__<tool>`, and the gateway tools may carry an `api_` prefix: `list_test_triggers`,
`list_test_chain_runs_for_trigger`, `get_test_blocks`, `get_test_block_versions`, `get_test_block_version`,
`get_test_chain_run_results`, `get_test_chain_run_environment`, `list_test_block_external_ids`,
`get_test_blocks_by_external_id`, `get_output_explorer_vocabulary` and `run_adhoc_assertions`. Call `get_org_context`
first; on a hosted server `set_organization` is unavailable, so do not claim which organization the data came from
unless a tool told you.

## Inputs

- **The requirements.** A paste, a file (CSV, markdown, a spreadsheet export) or a list of tickets. Keep the user's
  wording and IDs. If there are no IDs, number them R1, R2 and so on and say that you did. Do not rewrite, merge or
  split requirements. If one is ambiguous, ask what it means before mapping it.
- **The scope.** The pipeline, trigger, chain or test blocks the requirements apply to. Ask if it is not clear. If
  the user says "all of them", start from the active triggers.

## Procedure

1. **Read the requirements back.** Show them as a numbered list and say which, if any, you think a check could not
   test at all (a process or documentation requirement, for example). Confirm before mapping.
2. **Find the blocks.** `list_test_triggers` and `list_test_chain_runs_for_trigger` give a trigger's chain.
   `get_test_blocks(q=...)` finds blocks by name. Trigger and block names are not unique: identify by id.
3. **Read the current checks.** `get_test_block_versions(tb_id)` lists versions: use the one flagged current, not the
   newest by number. `get_test_block_version(version_id)` returns the assertions JSON. Read what each check does:
   the file pattern it reads, how rows are matched, which fields it compares, its thresholds and its `failtype`.
   Read it for structure; do not paste whole blobs. If the `assertion-explainer` skill is available, use it for the
   plain-words reading of a check.
4. **See what ran.** `get_test_chain_run_results` for a recent run of each chain shows which checks produced a result,
   and their status. A check with no result, or INCOMPLETE, or forced to pass, does not cover anything yet.
5. **Look for requirement IDs.** Results carry an `external_id` field. `list_test_block_external_ids` and
   `get_test_blocks_by_external_id` find checks that were tagged with a requirement ID. A tag is a claim by whoever
   wrote it: read the check before relying on it, and say when a tag and a check disagree.
6. **Map each requirement** to one of four classes, and name the check or checks and the block:
   - **Covered.** A check whose logic tests what the requirement says, that can fail the run, and that produced a
     result.
   - **Partly covered.** A check exists but tests less than the requirement says. Say which way, using these cases:
     it only checks that a file or column exists, not its values; it only compares with a baseline and sets no
     absolute limit; it is report-only or `failtype` warn, so it cannot fail the run; it exists on one chain and the
     requirement spans several; it skips some samples; it may find no file at all (`min_count` 0); it compares with
     the previous version and so passes by itself after a step.
   - **Not covered.** No check found. Say what you searched, so the reader can tell "none" from "did not look".
   - **Not testable by a check.** A requirement about process, documentation or a decision. List them apart and do not
     count them as gaps.
   A check name is a hint, not evidence. Where the logic is readable, map from the logic.
7. **Draft, do not write.** For each gap or partial, describe the check that would close it in a sentence: the file, the
   comparison and the outcome. Do not recommend a threshold value; if the user wants one, offer to propose a range from
   the existing data and show which samples it would flag. If the user wants the assertion itself, use the
   `assertion-translator` skill, and try it with `run_adhoc_assertions`, which saves nothing.
8. **Tagging (optional).** If the user wants the requirement IDs recorded on the checks that cover them, say what you
   would change, show the new assertions JSON, and wait for a yes. Editing a block replaces its checks and creates a
   new version at once, so show it first. (Untested: this stage has not been run end to end.)

## Reporting

Terminal first: counts by class, then a table with one row per requirement (ID, requirement, class, covering checks
and block, one line of why), then the gaps with a one-line draft for each, and the requirements a check cannot test.
Say what you did not read: blocks you did not open, runs you did not check.

## Optional private page

Offer it once. When asked, publish a private artifact laid out like this:

- **Tiles** across the top: covered, partly covered, not covered, in that order, with a count each. Add a fourth for
  requirements a check cannot test only if there are any.
- **A table**, one row per requirement: its ID, the requirement in the user's own words, a status pill (green for
  covered, amber for partly covered, red for not covered), the covering checks with their block, and one line of why.
  For a gap, the covering-checks cell says "no check".
- **A "close the gaps" card** with the one-line draft for each gap or partial. No threshold values.
- **A list of requirements a check cannot test**, set apart from the gaps.
- **A footer** with what was read (blocks and runs), what was not read, and the date.

Use theme-aware colors, keep block and run ids as plain text without links, and anonymize on request (generic
pipeline names, no registry paths). Say that the page is private and that others cannot open it until it is shared.
State in the page that it records what the checks do and makes no claim about whether a requirement is met, or about
regulatory or audit status. Do not publish without a yes.

## Never

- say a requirement is met, verified, validated, compliant or audit-ready;
- call a check adequate. Covered means a check exists that tests the thing;
- invent, reword or add requirements;
- map a requirement from a check's name alone when its logic can be read;
- count a check that cannot fail the run, or that has no result, as covering a requirement;
- change, create or tag anything before the user has confirmed it.
