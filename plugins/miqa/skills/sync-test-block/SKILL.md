---
name: sync-test-block
description: Use when the user wants to carry edits from one Miqa Test Block over to another, e.g. "this block was copied from that one and the original has changed since", "make block B match block A", "apply the changes I made between versions 12 and 15 of this block to the other one", "sync these two test blocks", "diff these two test blocks and update the copy" (via a connected Miqa MCP server). Two entry modes: compare two blocks and bring the target in line (A), or take the edits between two versions of a source block and replay them on a target (B). Classifies every difference (carry over / intentional for the target / ambiguous), shows the exact proposed assertions, and writes only after explicit confirmation. Not for browsing one block's history (use test-block-history) or explaining what a block checks (use assertion-explainer).
metadata:
  summary: Sync edits from one Test Block to another, with a reviewed diff and a confirmed write.
  version: 0.1.0
---

# Miqa Test Block Sync

Test blocks get copied (a second pipeline, a new dataset) and then the original
keeps evolving. This skill brings a **target** block in line with a **source**
block without clobbering what is deliberately different about the target, and
without writing anything the user has not seen first.

It reads with `api_get_test_blocks`, `api_get_test_block_versions` and
`api_get_test_block_version`, and writes with `api_update_test_block`, on
whichever Miqa MCP server is connected (tool names follow the pattern
`mcp__<server-name>__<tool>`). If more than one Miqa server is connected, ask
which one. Follow the server's org rule: call `get_org_context` once first, and
if the caller has several orgs and none is selected, ask which one.

## Two modes

- **Mode A: block vs. block.** "Make B match A." Diff the current source
  assertions against the current target assertions.
- **Mode B: replay my edits.** "Take what I changed in A between version N and
  M and do the same to B." Diff two versions of the *source*, then transplant
  that change onto the target's current assertions.

Pick the mode from the request. If it is unclear which one the user wants, ask
one question: "Compare the two blocks as they are now, or replay specific edits
you made to the source?"

## Preview first, write only on a separate explicit apply

**Every run is a preview. A run never writes.** Steps 1-7 are strictly
read-only and end with the change report and the line "Preview only: nothing
has been written to Miqa." That is a complete, successful outcome; most runs
should end there.

Writing is a separate, second action:
- Never call `api_update_test_block` in the same turn that produced the
  report. The user has to read the report and send a new message.
- Only an unambiguous instruction in that new message counts: "apply it",
  "yes, write it", "go ahead and update the target". Silence, "looks good",
  "nice", "ok", a question, or a request to tweak the report is **not**
  approval. When in doubt, don't write; ask.
- Approval covers exactly the report that was shown. If anything changes after
  the report (the user adjusts a bucket, the target gets a new version, you
  re-fetch and the diff differs), regenerate the report and ask again.
- Approval covers one target block. It is not carried to a second target or a
  later run.
- If the user said at the start "just preview" / "dry run" / "don't change
  anything", the write step is off for the whole session unless they say
  otherwise in so many words.
- Never offer to write as a default next step. Mention it once, as an option,
  at the end of the report.

The preview path calls no write tool at all (only `api_get_test_blocks`,
`api_get_test_block_versions`, `api_get_test_block_version`, the
docs/vocabulary lookups and, optionally, `api_run_adhoc_assertions` plus
`get_test_chain_run_environment` for validation, which read and persist
nothing).

## The write tool, and why this skill gates it

`api_update_test_block` is a **full replace** of the assertions, takes effect
**immediately, with no dry-run or preview**, and creates a new TestBlockVersion
on every call (even if nothing changed). It fails if the block is locked. So:

- The "dry run" is this skill's job: build the complete proposed assertions,
  show them in the change report, and wait for a separate explicit apply
  before calling the tool.
- Because every write is a new version, nothing is lost. The target's previous
  version stays in its history, which is the rollback path. Say so when asking
  for confirmation.
- Never call it on the source block. Never call it on a block the user did not
  name as the target.

## Procedure

1. **Resolve both blocks.** `api_get_test_blocks` with `q` set to each name the
   user gave. One match: proceed. Several: show id + name pairs and ask. None:
   try a looser substring before saying so. Confirm out loud which is the
   **source** and which is the **target** (a one-line "Source: X (id), Target: Y
   (id)") before going further; swapping them is the one expensive mistake here.

2. **Fetch the payloads.**
   - Mode A: current version of each block (`api_get_test_block_versions` with
     `limit=1`, then `api_get_test_block_version`).
   - Mode B: the two source versions the user named (resolve "before the typo
     fix" style references via `test-block-history`'s version table rather than
     asking for raw ids), plus the target's current version.
   Fetch in parallel. Note whether the target is locked if the response says so.

3. **Compute the structural diff.** Walk the `assertions` JSON by path (dot
   notation for objects, `[i]` for arrays), never a text diff of serialized
   JSON. Match checks by `name` within each `check_type` group, not by array
   index, since inserted or reordered checks shift indexes. Collect every
   added, removed and changed leaf.
   - Mode A: diff target to source.
   - Mode B: diff source version N to version M. That change set is the only
     thing to carry over; ignore any other source/target difference.

4. **Classify every difference.** Three buckets, and nothing goes unclassified:
   1. **Carry over.** A real edit in the source that the target lacks: a
      changed threshold, a renamed or added or removed check, a changed
      operator, a new `file_rules` entry.
   2. **Intentional for the target.** Looks deliberately different: different
      dataset or group references, file patterns or `baseline_override` paths
      that are pipeline-specific, thresholds that differ by pipeline, check
      names carrying a pipeline label. Leave these alone by default.
   3. **Ambiguous.** Can't tell whether the target diverged on purpose or just
      fell behind. Never guess; ask.
   In Mode A, a difference the target has and the source lacks (an extra check
   only in the target) is bucket 2 unless it clearly looks like something the
   source removed.

5. **Resolve the ambiguous items first.** Show the bucket 3 items (path, source
   value, target value, why it is unclear) and ask the user to rule on each.
   Offer to move anything between buckets; the user's call wins. Skip this
   step if bucket 3 is empty.

6. **Build the proposed assertions (the dry run).** Start from the target's
   current assertions and apply *only* the approved carry-over changes. Rules:
   - Preserve `_extends`, `_variables` and `_precompute` structure. Apply a
     change at the level it was made in the source (edit the shared variable if
     the source edited the variable, not every check that uses it).
   - Preserve target-specific `file_rules`, including any pattern-match or
     ignore pattern the target has, unless the change is to that pattern.
   - Keep references to Global Variables as references (by their name).
   - Do not reformat or reorder anything you are not changing.
   If the proposed assertions equal the target's current ones, say nothing
   needs to change and stop. Do not write an empty-change version.

7. **Generate the change report and stop.** Produce the report described in
   "The change report" below, in the format the user chose. End your turn
   there with "Preview only: nothing has been written to Miqa." plus a one-line
   note that you can apply it if they say so explicitly. Do not ask a yes/no
   and do not write in this turn. The report is the thing the user approves;
   never ask for a yes on a change they have not been shown in full.

   **Optional validation (only if the tool exists).** If this server exposes
   `api_run_adhoc_assertions`, offer in one line to run the proposed
   assertions against real executions before anyone applies them; it is
   synchronous and persists nothing. If the tool is not available, skip this
   silently apart from one line in the report: "Ad hoc validation is not
   available on this server; the proposed assertions have not been run against
   executions." Never block the report on it and never treat its absence as a
   failure. When the user accepts (or supplies executions):
   - Executions: use the pair the user gives (`exec_ids_test` /
     `exec_ids_baseline`, or `tbr_id_test` / `tbr_id_baseline`). Otherwise find
     them from the target block's latest completed run via
     `get_test_chain_run_environment` (it lists `testblock_id`,
     `testblockrun_id` and the baseline run). If there is no completed run, say
     so and stop; do not guess.
   - Run the full proposed blob (or at least every changed check) with
     `force_recheck: true`, and show per-check outcomes next to the target's
     current outcomes.
   - Limit: the call overrides `versions` with the supplied baseline, so a check
     whose `versions` is not `-1` (e.g. a release series) cannot be confirmed
     this way. Say so; do not call it verified.
   - A check that errors or fails to evaluate is a finding to report, not
     something to fix silently. Do not change the proposed assertions without
     regenerating the report.

8. **Write (only after a separate, explicit apply in a new message; see
   "Preview first").** Re-confirm with a single yes/no that states: the target block
   (name and id), how many changes, that this creates a new version immediately,
   and that the previous version remains in history to roll back to. On an
   explicit yes, call `api_update_test_block` with `body` set to the full
   proposed assertions JSON (the blob itself, not wrapped in an `assertions`
   key).
   - Leave `update_pinned_gv` at its default (false, keeps the prior version's
     global-variable pins) unless the user asks to pick up newer versions of
     global variables. If the source block was moved to a newer global-variable
     version as part of the edits, point that out and ask rather than assuming.
   - If the call fails because the block is locked, say so and stop. Do not
     work around it.

9. **Report.** One line on what changed. Per the server's rule, show every
   `resource_url` / `resource_urls` in the write result to the user. Mention the
   new version id if returned and where to find the previous version if they
   want to revert (`test-block-history`).

## The change report

The user must be able to understand exactly what will change, in plain
language, before they confirm. Ask once at the start of step 7 (unless they
already said): "Terminal summary, or an HTML report you can open and share?"
Default to terminal if they have no preference. Both formats carry the same
content, in this order:

1. **Header.** Source and target (name, id, version ids), mode, date, and a
   one-sentence plain-English summary of the whole change ("Brings Fusion Check B
   up to date with 4 edits made to Fusion Check A since the copy; 2
   differences are intentional and left alone").
2. **At a glance.** Counts per bucket: N carry over, N left alone, N you
   decided. A change that adds, removes or loosens a pass condition (threshold,
   operator, report-only vs. gating, check added or removed) is marked
   **affects what passes or fails**, so reviewers see behavioral changes
   separately from cosmetic ones (renames).
3. **Changes that will be made**, one entry per change (cluster related leaves
   that are one logical edit):
   - A short title ("Loosened coverage tolerance").
   - A plain-English explanation: what it was, what it becomes, and what that
     means for results. Ground any claim about what a check type or operator
     does in `get_output_explorer_vocabulary()` or the Miqa docs, as
     `assertion-explainer` does; if unconfirmed, say so rather than guess.
   - Where it came from: the source version, or the Mode B version pair.
   - A git-style diff for that change, in a ` ```diff ` fence in terminal output
     (red/green in the HTML), with `@@ <path> @@` hunk headers and `-`/`+`
     lines for only the leaves that differ. Show the whole diff even when long;
     never truncate a real change. For a large change set, list all entries
     first as a table of contents, then the detail.
4. **Left alone on purpose.** Each bucket 2 item with the source and target
   values side by side and the reason it was judged intentional or that the
   user ruled it so. This is what stops a reviewer wondering "did it miss
   this?".
5. **Combined diff.** The full target-current to proposed diff in one block, so
   they can see the final result in one place. Collapsed by default in HTML.
6. **What happens next.** Plain statement: confirming creates a new version of
   the target immediately; the previous version (give its id) stays in history
   to roll back to; nothing on the source changes.

**Terminal format.** Markdown with headings, a small summary table for step 2,
and ` ```diff ` blocks so the renderer colors them. No wall of JSON: only diff
hunks, never whole payloads, unless asked.

**HTML format.** Write a single self-contained `.html` file (inline CSS, no
external scripts), light and dark friendly, readable at phone width, with the
sections above, a sticky list of changes, colored diff blocks (red removed,
green added, monospace), and the combined diff in a collapsed `<details>`.
Save it in the session scratchpad and tell the user the full path. Publish it
as a private page with the Artifact tool only if the user asks to share it or
asks for a link; it contains assertions and check names, so don't publish
unprompted.

Whichever format, the report ends with "Preview only: nothing has been written
to Miqa." and no confirmation question. Keep the explanations short and specific; "Updated several fields"
is not an explanation.

## Notes

- Read freely; write once at most, only after the preview and a separate
  explicit apply, only to the named target. Approval of one write does not
  carry to a second target; ask again.
- Syncing to several targets: run steps 3-7 per target, because each has its
  own intentional differences.
- Match checks by name and group, not by array position.
- If both blocks use identical content except for target-specific values,
  that is a good sign the target should be a template or a shared Global
  Variable. Mention it once at the end, without acting on it. Don't suggest it
  when there are real divergences to keep.
- If the differences between source and target are so large that most of the
  target would change (a rewrite, not a sync), stop and say so before
  classifying everything; the user may want a fresh copy rather than a sync.
- This skill explains nothing about what individual checks mean. For that, hand
  off to `assertion-explainer`. For creating new checks in the same style, hand
  off to `assertion-translator`.
