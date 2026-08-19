---
name: test-block-history
description: Use when the user asks to check a Miqa TestBlock's "revision history", "version history", "what changed" on a test block, or wants a diff between two TestBlockVersions (via a connected Miqa MCP server). Resolves the block by name, lists its version history as a narrow table, then auto-diffs the most recent change as a plain-English summary plus a structural (path-based) diff.
metadata:
  version: 1.0.0
---

# Miqa TestBlock Revision History

Looks up a Miqa TestBlock by name, lists its version history, and diffs any
two versions — leading with a plain-English summary, backed by a structural
(path-based) diff of the underlying JSON rather than a literal line-based
`diff` of serialized JSON. Structural diffing avoids noise from key
reordering/whitespace and reads cleanly at narrow terminal widths, which a
textual `diff -u` on pretty-printed JSON does not.

This skill calls tools named `api_get_test_blocks`, `api_get_test_block_versions`,
and `api_get_test_block_version` on whichever Miqa MCP server is connected
(tool names follow the pattern `mcp__<server-name>__<tool>`). Most setups have
exactly one Miqa MCP server connected — just use it. If more than one is
connected, ask the user which one they mean before proceeding, rather than
guessing from the server name.

## Procedure

1. **Resolve the TestBlock.** Call `api_get_test_blocks` with `q` set to the
   name/substring the user gave. If exactly one match, proceed. If multiple
   match, show the id+name pairs and ask which one (don't guess). If zero
   match, try a looser substring before telling the user nothing was found.

2. **List version history.** Call `api_get_test_block_versions(tb_id)`. Post
   a narrow three-column table, newest first, before doing any diffing:

   | Version | Date created | Author |
   |---|---|---|
   | 🟢 1099 (current) | 2026-07-27 18:22 | Miqa Admin |
   | 1087 | 2026-07-21 00:17 | Miqa Admin |
   | 1000 | 2026-06-08 16:18 | Miqa Admin |

   Mark `is_current`/`is_latest` with a leading 🟢 plus inline "(current)"
   on the version id, don't add a separate column for it — keeps the table
   narrow while still popping visually against the plain rows below it.
   If `total_count` exceeds what was returned, note how many more exist and
   that older ones are available on request; don't auto-paginate the whole
   history up front.

3. **Auto-diff the most recent change — don't wait to be asked.** "What
   changed" is almost always the real question behind a revision-history
   ask, same as step 3 in the `active-triggers` skill leads with status
   before root cause. Take the two newest versions from step 2 (`current`
   and its `prev_version_id`), call `api_get_test_block_version` on both, and
   diff them per step 4 below. Skip this step only if there's just one
   version total (nothing to diff yet).

4. **Diff any two versions in two layers.** Fetch both versions via
   `api_get_test_block_version(version_id)` (each call already returns the
   full `assertions`/`instructions`/`meta_blob` payload plus its own
   `prev_version_id`, so a chain of diffs doesn't need re-fetching shared
   data). For the pair being compared:

   - **Plain-English summary first** — 1-2 sentences naming what actually
     changed in terms a non-engineer would recognize ("renamed a check,
     looks like a typo" / "the main preview table became downloadable" /
     "swapped the comparison source group from 1 to 3"). This is the
     headline; lead with it.
   - **Structural diff second, rendered as a colored `diff` block** — the
     underlying comparison is still structural (walk both JSON payloads by
     path, not a literal text diff of pretty-printed JSON — that's what
     avoids key-reordering/whitespace noise), but render the result inside
     a ` ```diff ` fenced code block so the renderer actually colors it red
     for removed / green for added, the same way a real `git diff` does.
     One hunk per changed leaf path, `@@ <path> @@` as the hunk header
     (instead of git's line-number range, since there's no source file —
     the JSON path *is* the location), then only the `-`/`+` line(s) for
     that leaf. Skip the `---`/`+++` file-header lines from real `diff`;
     replace them with a one-line comparison header naming both version
     ids + dates above the fence, since there's no filename to put there:

     Comparing TestBlockVersion **1087** (2026-07-21 00:17) → **1099** (2026-07-27 18:22):

     ```diff
     @@ assertions.tabular_mdo_eval.checks[0].name @@
     - .VCF: Tabular MDO: there are at least 1 rows in the file
     + .VCF: Tabuelar MDO: there are at least 1 rows in the file

     @@ assertions.tabular_mdo_eval.checks[0].table_config[0].downloadable @@
     + true
     ```

     An added key has only a `+` line (no prior `-` line); a removed key
     has only a `-` line. A changed leaf has both, `-` (old) directly above
     `+` (new). Only emit hunks for paths that actually differ — don't dump
     the whole payload as context lines around each change, since a
     structural diff doesn't need surrounding-line context the way a text
     diff does to locate the change; the `@@ path @@` header already
     locates it exactly. If a value is a long string/object, it's fine for
     the diff to run long; don't truncate a real change to keep the block
     short.
   - Only fall back to a literal unified `diff -u`-style text block instead
     of (not in addition to) the structural diff if the user explicitly asks
     for something `diff`-shaped to paste elsewhere (a PR comment, a ticket).
     Don't default to it — it's noisier and doesn't handle key reordering
     well.

5. **Offer to go deeper, don't dump it all.** After the auto-diff in step 3,
   ask whether the user wants: an older pair diffed, a specific two versions
   named directly, or the full raw payload of one version. Don't
   automatically diff every historical version pair — that's expensive and
   usually not what's wanted.

## Notes

- Always ship the version-history table (step 2) before diffing anything —
  it's one cheap call and orients the user on how much history exists.
- The most recent change is auto-diffed without being asked (step 3); older
  pairs are diffed on request only (step 5).
- Structural (path-based) diff is the default output format; literal
  unified diff is opt-in only, for when the user needs to paste it
  somewhere that expects `diff` syntax.
- Keep the plain-English summary to 1-2 sentences — it's a gloss on the
  structural diff below it, not a replacement for it. Never let the summary
  hand-wave past a field the structural diff would have caught.
