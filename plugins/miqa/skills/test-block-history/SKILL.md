---
name: test-block-history
description: Use when the user asks about a Miqa TestBlock's "revision history", "version history", "what changed" on a test block, wants a diff between two TestBlockVersions, or wants to grab a specific version's (or a single check's) assertions JSON to paste into the Miqa web UI (via a connected Miqa MCP server). Always starts with a browsable version-history table (with a lightweight per-row change gloss), then branches into either diffing a pair of versions or copying one version's content to the clipboard with paste instructions.
metadata:
  version: 1.0.0
---

# Miqa TestBlock Revision History

Nobody thinks in TestBlockVersion ids — they think in "the one before the
typo" or "whatever's live now." This skill always starts by resolving a
TestBlock and showing its version history as a browsable table with a
one-line change gloss per row, so the user can point at a version by
content. From there it branches two ways:

- **Dive deeper** — diff two versions, leading with a plain-English summary
  backed by a structural (path-based) diff rendered as colored `diff`
  syntax, not a literal text diff of serialized JSON (which is noisy on key
  reordering/whitespace).
- **Grab a version** — extract a whole version's `assertions` payload or a
  single check node, put it on the clipboard, and walk the user through
  exactly where to paste it in the Miqa web UI (merging into Output
  Explorer, editing a new version of the same TestBlock, or pasting into a
  duplicated TestBlock).

This skill calls tools named `api_get_test_blocks`, `api_get_test_block_versions`,
and `api_get_test_block_version` on whichever Miqa MCP server is connected
(tool names follow the pattern `mcp__<server-name>__<tool>`). Most setups
have exactly one Miqa MCP server connected — just use it. If more than one
is connected, ask the user which one they mean before proceeding. There is
no MCP tool to create/duplicate a TestBlock or write a new version — that
half is always a manual UI action this skill talks the user through, never
attempted via the API.

## Procedure

1. **Resolve the TestBlock.** Call `api_get_test_blocks` with `q` set to the
   name/substring the user gave. If exactly one match, proceed. If multiple
   match, show the id+name pairs and ask which one (don't guess). If zero
   match, try a looser substring before telling the user nothing was found.

2. **Show the version history table with a lightweight change gloss —
   don't wait to be asked, and don't assume they know a version id.** Call
   `api_get_test_block_versions(tb_id)` and post a table, newest first:

   | Version | Date created | Author | What changed (vs. previous) |
   |---|---|---|---|
   | 🟢 1099 (current) | 2026-07-27 18:22 | Miqa Admin | Renamed a check (typo: "Tabular" → "Tabuelar") |
   | 1087 | 2026-07-21 00:17 | Miqa Admin | Main preview table became downloadable |
   | 1000 | 2026-06-08 16:18 | Miqa Admin | — (initial version) |

   Mark `is_current`/`is_latest` with a leading 🟢 plus inline "(current)"
   on the version id, don't add a separate column for it — keeps the table
   narrow. Compute the gloss for the most recent 10 transitions by fetching
   each version via `api_get_test_block_version` and diffing consecutive
   pairs (same structural-diff approach as the "Diffing two versions"
   procedure below, condensed to one short clause — this table is for
   picking a version, not auditing one). If `total_count` exceeds 10, leave
   older rows' gloss as `—` and note more history exists with glosses
   available on request — don't silently truncate the table itself, only
   the gloss computation.

3. **Auto-diff the most recent change — don't wait to be asked.** "What
   changed" is almost always the real question behind a revision-history
   ask, same as step 3 in the `active-triggers` skill leads with status
   before root cause. Take the two newest versions from step 2 (`current`
   and its `prev_version_id` — already fetched while building the gloss
   column, no extra calls needed) and diff them per the "Diffing two
   versions" procedure below. Skip this step only if there's just one
   version total (nothing to diff yet).

4. **After the table + auto-diff, ask what's next — don't guess.** The two
   live paths from here:
   - **Dig deeper on a diff** — an older pair, a specific two versions named
     directly, or expanding one of step 3's 4b bullets into a full diff.
     Loop back into "Diffing two versions" below.
   - **Grab a version's content** — the whole payload or one named check,
     to paste somewhere. Jump to "Copying a version to the clipboard"
     below, using the version(s) already resolved in step 2's table (no
     need to re-resolve the TestBlock).

   If the user's original ask already made the destination obvious ("what
   changed" → stay in diff mode; "copy me the assertions from version X" /
   "I want to paste this into a new test block" → go straight to the copy
   flow), skip the question and proceed directly — this step exists for the
   genuinely ambiguous case, not as a mandatory stop every time.

### Diffing two versions

Fetch both versions via `api_get_test_block_version(version_id)` (each call
already returns the full `assertions`/`instructions`/`meta_blob` payload
plus its own `prev_version_id`, so a chain of diffs doesn't need
re-fetching shared data). Always compute the full structural diff first —
walk both JSON payloads by path (not a literal text diff of pretty-printed
JSON) and collect every changed/added/removed leaf, keyed by its full path
(dot notation for objects, `[i]` for array index). That complete leaf list
is what the two branches below work from — never approximate it from a
skim.

- **Plain-English summary, always first** — 1-2 sentences naming what
  actually changed in terms a non-engineer would recognize ("renamed a
  check, looks like a typo" / "the main preview table became downloadable"
  / "swapped the comparison source group from 1 to 3"). This is the
  headline in every case, small diff or large.

- **Small diff (5 or fewer changed leaves): show the full colored diff
  directly**, no gate. Render it inside a ` ```diff ` fenced code block so
  the renderer actually colors it red for removed / green for added, the
  same way a real `git diff` does. One hunk per changed leaf path, `@@
  <path> @@` as the hunk header (standing in for git's line-number range,
  since there's no source file — the JSON path *is* the location), then
  only the `-`/`+` line(s) for that leaf. Skip the `---`/`+++` file-header
  lines from real `diff`; replace them with a one-line comparison header
  naming both version ids + dates above the fence, since there's no
  filename to put there:

  Comparing TestBlockVersion **1087** (2026-07-21 00:17) → **1099** (2026-07-27 18:22):

  ```diff
  @@ assertions.tabular_mdo_eval.checks[0].name @@
  - .VCF: Tabular MDO: there are at least 1 rows in the file
  + .VCF: Tabuelar MDO: there are at least 1 rows in the file

  @@ assertions.tabular_mdo_eval.checks[0].table_config[0].downloadable @@
  + true
  ```

  An added key has only a `+` line (no prior `-` line); a removed key has
  only a `-` line. A changed leaf has both, `-` (old) directly above `+`
  (new). Only emit hunks for paths that actually differ — a structural diff
  doesn't need surrounding-line context the way a text diff does to locate
  the change, the `@@ path @@` header already locates it exactly. If a
  value is a long string/object, it's fine for the diff to run long; don't
  truncate a real change to keep the block short.

- **Large diff (more than 5 changed leaves): lead with a bulleted change
  list instead of the raw diff — don't dump 20+ hunks on someone.** One
  bullet per changed leaf (or, if several leaves are clearly one logical
  edit — e.g. every field inside the same `checks[i]` entry changed
  together — one bullet per logical cluster naming how many fields it
  touched), each bullet a short plain-English clause with the path in
  backticks so it stays precise, not vague prose:

  - Renamed `checks[0].name` (typo: "Tabular" → "Tabuelar")
  - `checks[2]` (the "Depth Coverage" check) had 4 fields changed:
    `min_count`, `stat`, `evidence`, `table_config[0].downloadable`
  - Added a new check `checks[3]` ("Contig Count")
  - Removed check `checks[4]` ("Legacy MDO")

  Then stop and ask whether they want the full colored diff for everything,
  or just for specific bullets — don't auto-expand the whole thing. Same
  "headline first, detail on request" shape as `active-triggers` step 3's
  quick table before step 6's root-cause table — don't collapse the two
  into one giant wall of output.

- Only fall back to a literal unified `diff -u`-style text block instead of
  (not in addition to) the above if the user explicitly asks for something
  `diff`-shaped to paste elsewhere (a PR comment, a ticket). Don't default
  to it — it's noisier and doesn't handle key reordering well.

- The 5-leaf threshold is a starting point, not a hard rule — a 6-leaf diff
  that's all one obvious logical edit can still get the full diff directly,
  and a 4-leaf diff spanning four unrelated checks might read better as
  bullets. Judge by "would this diff be legible at a glance," not the raw
  count.

### Copying a version to the clipboard

1. **Confirm the version and scope.** The version should already be
   resolved from step 2's table (or a further version named mid-diff). If
   it isn't yet, resolve it from that table rather than asking for a raw
   id. Then determine scope: whole version vs. a single check. If the user
   said "the whole thing"/"everything", or didn't mention a specific check,
   copy the entire `assertions` object (not the whole version payload —
   `instructions`/`meta_blob`/`id` aren't part of what the Output Explorer
   assertions editor expects). If they named a specific check ("the depth
   coverage check", "the Smaller Table check"), search every check_type
   group's `checks[]` array in the fetched `assertions` for a name match —
   assertions are nested `assertions.<check_type>.checks[]`, a single
   version can have checks spread across more than one check_type — and
   extract just that one check object. If the name is ambiguous or you
   can't find a confident match, list the check names you did find and ask
   rather than guessing which one they meant.

2. **Copy the extracted JSON to the clipboard.** Write it to a temp file in
   the session scratchpad first (avoids shell-quoting problems with
   quotes/special characters inside the JSON), then pipe it to the
   platform clipboard command — `pbcopy` on macOS, `clip.exe` on
   WSL/Windows, `xclip -selection clipboard` or `xsel --clipboard --input`
   on Linux (check which is installed; if neither is, say so and print the
   JSON in a fenced code block for manual copy instead of silently
   failing). Confirm what's now on the clipboard in one line — what it is,
   how many checks if it's the whole payload, roughly how large — don't
   silently assume the copy worked without saying so.

3. **Ask (or infer from phrasing) which of the three destinations they
   want, then give destination-specific instructions.** Derive the Miqa web
   UI host the same way `active-triggers` does: read the `MIQA_SERVER_URL`
   env var backing the connected MCP server; if it's `api.<env>.miqa.io`-
   shaped, the web host is `<env>.miqa.io` (strip the leading `api.`);
   otherwise don't fabricate a link, describe navigation in words instead.

   - **Merge into the Output Explorer assertions view.** Tell them to make
     sure focus is *not* inside the JSON editor — click anywhere else on
     the Output Explorer page first — then press **Cmd+Shift+V**. That
     triggers a merge-paste of the clipboard JSON into the existing
     assertions rather than a plain overwrite. Warn explicitly: pasting
     while focus IS inside the JSON editor (or a plain Cmd+V anywhere) does
     a normal literal paste, not the merge — that's the mistake this
     instruction exists to prevent.

   - **Paste as a new version of the same TestBlock.** Give them
     `{web_host}/test_block/{tb_id}`, tell them to scroll to the
     **Assertions** section and click **Edit**. Then:
     - Whole payload → select all in the JSON editor and paste over it.
     - Single check → don't just say "paste it in" — say exactly where,
       using the check list already pulled (e.g. "paste it as a new entry
       in `assertions.tabular_mdo_eval.checks`, right after the 'Smaller
       Table' check" or "as check index 2"). You already know the current
       version's check ordering from the earlier fetch — use that, don't
       make the user hunt for the right spot.

   - **Paste into a brand-new TestBlock (not a new version of this one).**
     Tell them to duplicate first: on the **parent** TestBlock's page, open
     the **Quick Actions** menu → **Duplicate**. That creates a new
     TestBlock pre-populated as a copy. Then follow the same paste
     instructions as the "new version" bullet above, but on the duplicate's
     Assertions editor, not the original's.

## Notes

- Always ship the version-history table (step 2) before diffing or copying
  anything — it's cheap and orients the user on how much history exists
  and lets them point at a version by content instead of an id.
- The most recent change is auto-diffed without being asked (step 3);
  older pairs, specific pairs, and copy-to-clipboard requests all happen
  on request (step 4).
- Structural (path-based) diff is the default underlying comparison for
  both the gloss column and the full diff; literal `diff -u` text diff is
  opt-in only, for when the user needs to paste it somewhere that expects
  `diff` syntax.
- Keep the plain-English summary to 1-2 sentences — it's a gloss on the
  diff below it, not a replacement for it. Same for the large-diff bullets:
  each one names the *what* precisely (path + short clause), never
  hand-waves past a real change the way "several fields were updated"
  would.
- Never let the bulleted large-diff summary stand in for the full diff
  permanently — it's a first pass so the user isn't drowned in hunks,
  always paired with an explicit offer to expand.
- This skill only ever reads (`api_get_test_block*`) for the copy flow — it
  never calls anything that writes a new TestBlock or TestBlockVersion.
  Every write (Duplicate, Edit + paste, the Cmd+Shift+V merge) is a manual
  step the user does in the web UI; describing it precisely is the
  deliverable.
- For a single-check copy destined for an edit/duplicate flow, always cite
  the destination location using the source version's own check
  ordering/names — a vague "paste it in the checks array somewhere"
  defeats the point of that flow.
