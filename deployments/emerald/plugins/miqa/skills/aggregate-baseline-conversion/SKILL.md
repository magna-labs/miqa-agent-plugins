---
name: aggregate-baseline-conversion
description: Use when the user wants to convert an existing Miqa Test Block whose baseline side is a static aggregate source (a baseline override, baseline file rules, or a pinned reference version pointing at a precompiled file) into a direct comparison between two real executions, e.g. "convert Test Block N from R&D-vs-prod to prod-vs-prod", "remove the aggregate baseline from this block", "make a regression version of this block". Reads the existing assertions, infers how the aggregate works, asks narrowing questions, converts one representative check, then the rest, and saves only a shareable Output Explorer link. Never creates or changes a Test Block unless the user explicitly asks at the end.
---

# Aggregate Baseline Conversion

Convert a Test Block's assertions so that baseline and test are both real executions, instead of the baseline being a
static aggregate source. Everything specific (file names, column names, field paths, check types) is inferred from the
existing assertions and the executions. Nothing about any particular pipeline belongs in this file.

Defer to the sibling skills instead of repeating them:

- `assertion-explainer` — use it first to read the original block and explain how each check works.
- `assertion-translator` — use its documentation lookup, vocabulary, validation and save-a-link rules to write and
  check the converted assertions. Its publish gate applies here unchanged.
- `test-block-history` — optional, for diffing against an earlier version of the block.

## Inputs

- The Test Block ID (the source).
- A baseline execution ID and a test execution ID. If only one exists, use it for both sides and say plainly that
  nothing can fail yet, so a pass proves the config resolves, not that a real regression would be caught.

If a bare number could be an Execution, a Test Chain Run or a Test Block, ask which. Never infer it from the range.
Resolve a Test Chain Run to its executions before inspecting outputs.

## Step 1 — Read and classify (nothing written yet)

Fetch the block's current version and walk every check. For each, decide where the baseline value comes from. Do not
decide from `versions` alone: `-1` with a baseline override can still be an aggregate, and a named version without an
override can be an ordinary comparison. Look at:

- baseline overrides, baseline file rules, and baseline file patterns that differ from the test side
- what the baseline expressions read (rows keyed by a sample or order identifier, a precompiled table) versus what the
  test-side expressions read
- anything that exists only to look up one sample inside a multi-sample baseline file

The test side shows the production-side path already. The converted baseline side should read the same kind of data
from the baseline execution. **The check type follows the test side's data.** Change it only if the test side's data
requires a different type, and say so.

**Keep by default:** metrics, match keys and grouping, thresholds and relationships, rounding, skip lists, force-pass
flags, aggregate tolerances, `single_file`, and `min_similarity_score`. Remove only what exists solely to point the
baseline at the static source (the override, the baseline file rules, a pinned baseline version). If you cannot tell
whether a setting is aggregate-only, keep it and ask.

## Step 2 — Confirm against the executions

Call `inspect_execution_outputs` on both executions. Confirm the files, columns or stats the converted baseline side
needs actually exist on the baseline execution. If a needed source is missing, stop and report it. Do not substitute a
guess.

## Step 3 — Ask before changing anything the user may care about

Ask the narrowing questions below only when the assertions and executions cannot settle them. Group them in one
message. Skip any question that has nothing to ask about; never ask the user to confirm that there is nothing to
decide. If no question applies at all, go straight to Step 4.

1. **Checks that do not convert.** Ask this only if there is at least one. If every check converts, say nothing about
   it here; the per-check table in the report shows all converted and nothing dropped. Never ask the user to confirm
   a "none". List every check you think does not convert cleanly (for example it reads only the
   baseline, or it has no test-side equivalent). For each: name, reason, and a proposed action — drop, keep as is, or
   convert another way. The user approves or changes each one. **Never drop a check without approval.** A check that
   looks only at the baseline is the usual reason to propose a drop; a baseline column with no counterpart on the
   other side is not, because conversion follows what the test side checks.
2. **Names and labels.** Check names, chart titles and axis labels may carry the old baseline's wording. Ask whether to
   rename them.
3. **Thresholds.** Ask whether to keep them as they are or loosen some (for example fail to warn). This is the
   user's decision; do not volunteer a change.
4. **Anything else you would otherwise decide silently:** a changed check type, a changed way of computing a value, a
   removed setting you were unsure about. Report each with a reason.

## Step 4 — Convert one check, evaluate, then the rest

1. Pick one representative check. Translate it and evaluate it with `api_run_adhoc_assertions` against the baseline and
   test executions. Nothing is saved. Show the result and wait if it looks wrong.
2. Translate the rest. Validate with the `assertion-translator` validator. If it reports reference failures for
   variables that each check supplies through `_extends`, compare against the original block: the same failures there
   mean the live run is the real test.
3. Run the full converted blob live. Every source check must appear in the result.

Practical notes:

- Ad-hoc run output can be very large. It is saved to a file; query it with `jq`.
- Check the live documentation for what each check type exposes on the baseline side before writing expressions. Do
  not assume a feature that works in one check type (for example named precomputed values) works in another. If a
  check evaluates to no outcome with no error, suspect that first; try check-level `_variables` with `{{ }}`
  substitution.
- Use the `assertion-translator` rules for outcome shape, `detail_display_stat`, and description fields.

## Step 5 — Report and link, together

Once Step 4's full live run is done, produce both in the same step, without asking permission for either: the HTML
report below, and the shareable Output Explorer link (Step 6). Put the link in the report's summary strip as well.
If a Step 3 question is still unanswered and changes the assertions, resolve it first; do not save a link for
assertions you know are wrong.

Build the report as a single HTML page and publish it with the Artifact tool (private by default). Load the
`artifact-design` skill first. In the terminal, give a short summary, the report link and the Output Explorer link;
do not repeat the whole report.

The page, in this order:

1. **Summary strip:** source block, baseline and test execution IDs, checks in / checks out / approved drops, and a
   plain-language status (for example "resolves; cannot fail yet — same execution on both sides").
2. **What changed and why:** a short list of the conversion decisions (what was removed, what the baseline now reads,
   any check-type change), each with its reason. This is the part a reviewer reads first.
3. **Per-check table:** every source check, one row each — converted, converted with a change (say what), or dropped
   with approval. The counts must reconcile. A check missing from the table is a bug. Use grouping or collapsible
   sections if there are many near-identical rows.
4. **Diffs, git-style.** Produce them with `diff -u` on key-sorted, pretty-printed JSON of the before and after
   assertions, then render the unified output: `-` lines in red, `+` lines in green, `@@` hunk headers muted, a few
   lines of context, monospace. Do not hand-write diffs.
   - Show the representative check's unified diff open by default.
   - Put the rest in collapsible sections, one per distinct shape (for example the shared template or variables, then
     one per kind of check), not one per near-identical check. Say how many checks each diff stands for.
   - State if the "before" was reconstructed and not byte-identical.
5. **Unresolved issues and what this cannot prove**, including the same-execution caveat when it applies.
6. **The proposed assertions**, in a collapsible block with a copy button.

Keep the same layout and design every run so reports are comparable. Do not put anything from the report that you
would not show the user in the terminal; it is a presentation of the same facts, not extra claims.

## Step 6 — Output Explorer link, then offer a block

Save the converted assertions as a shareable Output Explorer link with the `assertion-translator` save tooling, at the
same time as the report. This is the user's standing approval for this skill, so do not ask first; it overrides the
translator's ask-before-saving step for this one scratch record only. Keep the translator's other rules: a name and
description that identify the source block and date, and the link pinned to the baseline/test pair.

Report the link plainly, and say that it creates no Test Block and changes nothing, and that anyone holding the link
can open the assertions (it has no organization scoping). Then ask one thing: "Want it on your clipboard?" If yes,
copy it with `pbcopy` (macOS) or the platform equivalent.

After that, ask whether they want it to become a block. If yes:

- If they want it separate from the original, tell them to duplicate the original block first and give you the new
  block's ID.
- Show what will be replaced, get explicit confirmation, then update that block. Never update the original unless the
  user says to.
