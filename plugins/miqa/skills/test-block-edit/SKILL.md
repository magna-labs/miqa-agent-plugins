---
name: test-block-edit
description: Use when the user wants to add, change or remove checks on an EXISTING Miqa Test Block (e.g. "add a check to this test block", "make SNP F1 fail if it moves more than 1%", "tighten these thresholds on TB 382") via a connected Miqa MCP server. Fetches the block's current assertions, drafts the change as a merge (never a bare replace), validates it ad hoc, shows a diff, and only writes after explicit approval. Not for drafting assertions from scratch (use assertion-translator) or reviewing past versions (use test-block-history).
metadata:
  version: 0.1.0
---

# Edit an existing Test Block

`api_update_test_block` is a **full replace**. It takes effect immediately, has no preview, creates a
new TestBlockVersion on every call, and fails if the block is locked. Everything this skill does is
about not getting that wrong. `assertion-translator` never changes a Test Block; this skill is the
one place that does, and only with approval.

## Workflow

1. **Resolve the block and org.** Call `get_org_context` first. With several organizations and none
   selected, ask once and call `set_organization`. If the user names a trigger or a test, resolve
   the Test Block id through `list_test_triggers` and the trigger's latest run
   (`list_test_chain_runs_for_trigger` → `get_test_chain_run_environment`, which lists
   `testblock_id`, `testblockrun_id` and the baseline run). Trigger and chain names are not unique:
   when more than one matches, list them and ask.
2. **Fetch the current assertions.** `api_get_test_block_versions` for the current version id, then
   `api_get_test_block_version`. Keep this JSON verbatim: it is the base of the merge and the
   rollback point. Note the version id.
3. **Draft the change** with `assertion-translator`'s rules (group key = `check_type`, the
   vocabulary from `get_output_explorer_vocabulary`, `description` on every check, baseline
   inheritance). Do not hand-roll check shapes from memory.
4. **Merge, don't replace.** The new body is the fetched assertions plus the change. Every
   untouched group and check must come through byte-for-byte. State plainly what is untouched.
5. **Settle intent before writing**, asking only what the request left open: add alongside vs
   replace an existing check, direction (either / drop only), relative vs absolute, and `failtype`.
   Do not default to `fail`.
6. **Validate ad hoc** with `api_run_adhoc_assertions`, passing the latest run's `tbr_id_test` and
   baseline `tbr_id_baseline` from `get_test_chain_run_environment`, with `force_recheck: true`.
   Run the full merged blob, or at least every new or changed check. Note that this call overrides
   `versions` with the supplied baseline, so it cannot confirm that a non-`-1` value such as
   `@release_series` resolves. Say so; do not call such a check verified.
7. **Show the diff and wait.** Present the added, changed and removed checks, the ad hoc results,
   and any assumptions (e.g. `versions` copied from sibling checks). Ask for explicit approval to
   write. A reply to a clarifying question is not approval.
8. **Write, then verify.** Call `api_update_test_block` with the merged assertions as the body (the
   body IS the assertions blob, not wrapped). Leave `update_pinned_gv` unset unless the user asked.
   Then re-fetch with `api_get_test_block_versions` and `api_get_test_block_version`, compare the
   saved assertions with what was sent, and report the new version id and the rollback version id.

## Rules

- Never call `api_update_test_block` before step 7's approval, and never with a body you have not
  merged against the freshly fetched current version.
- Every update creates a version, including a no-op. Do not retry a write to "make sure".
- If the write succeeds but the re-fetch differs from what was sent, report the difference
  rather than rewriting.
- A new `fail`-severity check changes how existing triggers report. Say which trigger this block
  belongs to and that its next run is the first real test.
- Rolling back means re-publishing the previous version's assertions. Offer it, do not do it
  unprompted.
