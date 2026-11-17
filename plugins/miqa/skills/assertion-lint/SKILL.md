---
name: assertion-lint
description: Use when the user asks to lint, review, sanity-check or tidy a Miqa Test Block or a set of assertions, e.g. "lint this test block", "what's wrong with these assertions", "why does this check never fail", "can this block be faster", "find the mistakes in this check", or pastes assertions JSON and asks whether it is correct (via a connected Miqa MCP server). Reads the assertions, finds structural errors, checks that each check can actually pass and fail the way its name says, flags names used in the wrong place, and suggests reuse and performance improvements. Report-only: it never edits, saves or publishes a Test Block. Afterward it offers a shareable one-page HTML report with before-and-after diffs of the fixes.
metadata:
  summary: Lint a Test Block's assertions for errors, unclear pass/fail, and reuse or performance problems.
  version: 0.2.0
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
   the smallest edit that fixes it. Finish with what you could not check. Offer to apply the fixes only if the
   user has not already asked: as a new Test Block version, or, in the Miqa web chat, as an Apply
   block (see below).

8. **Offer a report, once.** After the written report, say that a shareable one-page report is
   available, with a git-style before-and-after diff for each fix. State it once and do not re-offer.
   Build nothing unless the user says yes.

   When they do, use `reference/template.html` in this skill's folder as the literal starting file:
   copy it verbatim and fill in only the `{{PLACEHOLDER}}` tokens and the repeated blocks. Then delete
   every HTML comment from the page, because the instructions in them must not appear on it. Do not
   restyle it. Its header lists the content rules. The page says what the written report said and
   nothing more: the same findings, severities, rule ids and check positions.

   For each finding that has a fix you are confident in, add a diff:
   - Take the check as it is now and as it would be after the fix, each pretty-printed as JSON with
     two-space indentation. Compare them line by line, and keep three lines of unchanged context
     around each change. In Claude Code you can run `diff -u` on two files. In the web chat there is
     no shell, so compare them yourself.
   - Write each line as a `.dl` row in the template's `.diff` block: removed lines with `del`, added
     lines with `add`, and the old and new line numbers in the two number columns. Escape `&`, `<` and
     `>` in every line, and put long runs of unchanged lines in a `<details>`.
   - If you proved the rewrite with `api_run_adhoc_assertions`, add the `.proof` line saying so.
     Otherwise leave it out.

   Deliver it for the environment you are in:
   - **Claude Code with an artifact tool:** publish it as a private page, titled with the block's
     name followed by "Lint" (or "Assertions Lint" for a pasted blob), and give the user the link.
   - **The Miqa web chat** (the turn has page context, and there is no filesystem or clipboard): put
     the filled template in **one** fenced code block whose language is `miqa-html`, holding the whole
     document. The drawer shows an **Open report** button under it. This is a separate block from the
     `miqa-assertions` block that carries the fixes, so send them as two blocks, and never ask the
     user to save or paste the HTML.
   - **Neither:** say you cannot make the page here.

## In the Miqa web chat

When the page's editor JSON is in the turn's context ("Assertions JSON in the page editor"), the
fixes can be applied to the editor. Give the report first. Then, if the user asked for fixes or says
yes when you offer them, put the fixes in a block like this:

- Send **one** fenced code block whose language is `miqa-assertions`. It holds only the check-type
  groups to change, each with a `checks` list of **complete** corrected checks. The drawer shows an
  **Apply** button under it, so never ask the user to paste the JSON.
- Apply replaces a check with the same `name`, so keep every changed check's `name` exactly as it
  is. A check with a new name is added at the top, and it leaves the old one in place. Do not rename a
  check in a fix. If a rename is needed, tell the user to delete the old check by hand.
- Top-level `_variables` is merged shallowly: you can add or overwrite entries, not remove them.
- Apply cannot delete. Deleting a whole check, or an entry in top-level `_variables`, has to be done
  by hand: list those separately in plain words. Removing a key from inside a check is fine, because
  the whole check is replaced.
- Checks with no `name`, or with the same `name` as another check, cannot be targeted reliably. Leave
  them out of the block, and say they need a manual edit.
- Apply only fills the editor. It does not save. Tell the user to review the editor and save it.
- Include only fixes you are confident in, or have proven. Leave suggestions that need a decision from
  the user as text.
- If the context says the editor JSON was omitted for size, read the block with
  `api_get_test_block_version`, or ask the user to paste it. Apply still works on the page's editor.

## Things to watch

- A large version result may arrive truncated or be saved to a file. Parse the file with
  `python3 -I` or `jq` instead of reading it whole, and say if you could not read all of it.

- `relationship` is the condition under which a check **fails** in almost every check type. In
  `file_counts` it is the **pass** condition. Get the direction right before you flag one.
- A placeholder `stat` with `static: 0` and `relationship: "lt"` is normal on a check with
  `aggregate_check_only`. Do not flag it there.
- A per-sample `table_config` beside an aggregate table that covers the same data is rule R3, even
  when it is `download_only`. A `download_only` table is still evaluated and stored for every
  sample. Raise it as a suggestion, and lower its priority when there are only a few samples.
