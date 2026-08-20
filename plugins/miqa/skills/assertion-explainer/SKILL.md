---
name: assertion-explainer
description: Use when the user asks "what is this test block testing", "explain these assertions", "what does this check do", "walk me through this Test Block", or pastes/references a Miqa Output Explorer assertions JSON blob (from a connected TestBlock, a paste, or one already fetched earlier in the conversation) and wants a plain-English readout. The reverse direction of assertion-translator — takes an already-written assertions blob and explains what it actually checks, grounded in live Output Explorer vocabulary and MIQA docs rather than guessed from memory.
metadata:
  version: 1.1.0
---

# Miqa Assertion Explainer

`assertion-translator` goes prose/script → DSL. This skill goes the other way: an
existing TestBlockVersion's `assertions` JSON → a plain-English account of what a
reviewer actually gets checked. Same DSL, same evidence discipline — this skill
never explains a `check_type`, operator, or template by guessing what it probably
does; it grounds every claim in `get_output_explorer_vocabulary()` and the MIQA
docs, the same way `assertion-translator` grounds its translations.

This skill calls tools named `api_get_test_blocks`, `api_get_test_block_versions`,
`api_get_test_block_version`, and `get_output_explorer_vocabulary` on whichever Miqa
MCP server is connected (tool names follow the pattern `mcp__<server-name>__<tool>`).
Most setups have exactly one Miqa MCP server connected — just use it. It only ever
reads; it never calls anything that writes or publishes.

## Procedure

1. **Resolve the assertions payload.** There are three ways in — figure out
   which one applies before calling anything:
   - **Pasted or inline JSON.** The user drops an `assertions` blob (or a
     single check object) directly into the prompt. Use it as-is — no MCP
     resolution needed. If it doesn't parse as valid JSON, or looks like a
     truncated fragment (e.g. a lone `checks[]` array with no enclosing
     `check_type` key), say what's wrong or ambiguous about it before
     proceeding rather than guessing the missing structure. A pasted blob has
     no TestBlock id, version id, author, or date attached — don't invent
     one; the overview in step 5 just won't cite those.
   - **Already in conversation context.** The user references a payload
     already fetched earlier in this same conversation (e.g. "explain the
     ci-smoke one from before," "what about that JSON you just pulled").
     Reuse it directly — don't re-fetch. If enough has happened since that
     the version could plausibly have changed (a long gap, an intervening
     edit discussion), say you're working from the earlier fetch rather than
     re-confirming silently; re-fetch only if the user asks or if staleness
     actually matters for what they're asking.
   - **A named TestBlock (the common case).** Call
     `api_get_test_blocks(q=<name>)`. Zero or multiple matches → follow the
     same resolution rule as `test-block-history` step 1: don't guess, show
     the id+name pairs and ask if there's more than one. Once resolved, pick
     the version:
     - No version specified → the current one. Call
       `api_get_test_block_versions(tb_id, limit=1)` and take
       `current_version_id`.
     - A specific version named (an id, "the one from last Tuesday", "before
       the August 10 edit") → resolve it the way `test-block-history` does,
       using that skill's version-history table if the user needs to browse
       for it. Don't re-explain that resolution flow here — invoke it.

     Fetch the full payload with `api_get_test_block_version(version_id)`.

2. **Ground the vocabulary before explaining anything.** Call
   `get_output_explorer_vocabulary()` once and keep its payload for the rest of
   the pass. Use it to confirm what each `check_type` and comparison operator
   actually means — never explain one from memory. If a `check_type` or field
   in the payload isn't covered by the vocabulary call, check the MIQA docs via
   `$MIQA_DOCS_BASE_URL/<path>` using the path table in
   `../assertion-translator/references/doc-paths.md` (same base-URL resolution
   rule as that skill: if `MIQA_DOCS_BASE_URL` isn't set, say so and explain
   what you can from structure alone rather than stopping entirely — explaining
   is lower-stakes than publishing, so a partial answer with an explicit gap is
   fine here). If neither source resolves it, say plainly that this check
   type/field is unconfirmed rather than inventing a plausible-sounding
   explanation.

3. **Resolve templating before interpreting semantics.** Assertions blobs
   commonly use `_extends`/`_variables`/`_precompute` to define a check once and
   stamp it out with different field names per check (this is exactly what
   `[detection] ci-smoke`'s `PAIRED_EXEC_STAT_EVAL` and `JSON_COMPARE_TO_AGG_CSV`
   templates do). Resolve every check the way the runtime would — per
   `../assertion-translator/references/variables-and-precompute.md` — before
   explaining it: substitute `_variables` into the template, merge `_extends`
   bundles, and note any `_precompute` bindings the `stat`/`table_config`/
   `chart_config` expressions rely on. Explain the **resolved** comparison (e.g.
   "compares `baseline_execution_stats.call_mrd.tfx` to
   `test_execution_stats.merged_qc_json.cfdna.Tfx`"), never the raw
   `{{BASELINE}}`/`{{TEST}}` placeholders — a reviewer asking "what is this
   testing" wants the concrete fields, not the template shorthand.

4. **Interpret each check** using the same checklist `assertion-translator`
   uses to go the other direction, read in reverse:
   - **Data scope** — what file(s) or execution-stats namespace is this
     reading (`file_rules.pattern`, `versions: [-1]` = current version only,
     `baseline_override` = a pinned/fixed reference file rather than "this
     trigger's baseline run", `execution_stats.*` = pipeline-level stats
     rather than an output file at all)?
   - **Comparison mode and match keys** — baseline vs. test, paired execution
     stats, a `compare_by`/`compare_fields`/`compare_all_fields` sequence
     comparison (name the match key), or a standalone assertion on one side
     only?
   - **The actual computation** — what specific fields are being compared or
     computed, using their resolved (not templated) names?
   - **Pass condition** — exact equality vs. `approx_equal` (float tolerance)
     vs. a threshold vs. report-only (no gate, `report: true` with no
     `relationship`/`threshold`). Call out explicitly wherever an exact match
     is required on an otherwise-approximate check group (e.g. a categorical
     status field sitting in a group of otherwise-tolerant numeric
     comparisons) — that's usually the one field a regression would actually
     be caught on.
   - **Anomalies** — a check whose `_variables` are byte-for-byte identical to
     another check in the same list (a likely accidental duplicate), a
     `file_rules.pattern` that looks unusually narrow or broad, a
     `baseline_override` pointing at a fixed path instead of a normal
     baseline run. Flag these, don't silently normalize them away.

5. **Write the explanation.** Group by `check_type`, and within a `check_type`
   group by the underlying `_extends` template when one is used — explain the
   template's shape once, then list what varies per check as a compact table
   (field pairs, match keys, whatever differs), the same way you'd explain "11
   checks all comparing a baseline execution stat to the matching
   `merged_qc.json` field" once instead of restating the same sentence 11
   times. Lead with one or two sentences on what the payload is for overall
   (what pipeline/output it's guarding, inferred from the fields and file
   patterns actually present — not from the TestBlock's name alone, since
   names drift from content). If it came from a resolved TestBlock, name it
   and its version; for a pasted or already-in-context blob with no
   TestBlock identity, just skip that framing rather than fabricating a name.
   End with any anomalies from step 4 as a short "Notes" list, not buried
   mid-explanation.

   For a TestBlock with only a handful of checks and no shared template, skip
   the grouping ceremony and just walk through each check directly — the
   grouped-table format exists to keep a large, templated block legible, not
   as a mandatory structure for every explanation.

6. **Point forward, don't duplicate.** If the payload came from a resolved
   TestBlock and the user wants version history, a diff against an older
   version, or to copy this version's assertions somewhere, hand off to
   `test-block-history` rather than reimplementing that here (a pasted or
   already-in-context blob has no version history to hand off to — nothing to
   do here in that case). If the user wants to add or change a check in this
   same style, hand off to `assertion-translator` regardless of where the
   payload came from. This skill's job ends at "here's what it currently
   checks."

## Notes

- Every claim about what a `check_type` or operator means traces back to
  `get_output_explorer_vocabulary()` or a cited MIQA doc path — never explain
  DSL semantics from memory, same rule `assertion-translator` follows in the
  translate direction.
- Resolve `_extends`/`_variables`/`_precompute` before explaining, always. An
  explanation built from the raw templated JSON (still showing `{{BASELINE}}`
  or `$name` placeholders) hasn't actually explained anything.
- A duplicate check, a pinned `baseline_override`, or a lone exact-match field
  inside an otherwise-approximate group is exactly the kind of thing worth
  surfacing — this skill's value is catching what a quick skim of the raw JSON
  would miss, not just re-narrating field names.
- Read-only: this skill never calls anything that creates or edits a
  TestBlock, TestBlockVersion, or ad-hoc assertions record.
