---
name: version-rollup
description: Use when the user asks to "show all results for version/docker tag X", "get me everything that ran on build X", or otherwise wants a rollup of every Miqa test chain run for one specific version/docker tag (via a connected Miqa MCP server) — across every component and test chain, not scoped to a single trigger. Produces a per-check tally table, then flags anything failing or warning.
metadata:
  version: 1.1.0
---

# Miqa Version Rollup

Given one docker tag (a specific build), finds every Miqa Test Chain Run
across every component/test chain that used it and reports a per-check
pass/warn/fail tally for each — a horizontal slice across one build,
rather than the vertical per-trigger view the `active-triggers` skill
produces.

This skill calls tools named `list_test_chain_runs`, `find_test_chain_runs_by_version`,
and `get_test_chain_run_results` on whichever Miqa MCP server is connected
(tool names follow the pattern `mcp__<server-name>__<tool>`). Most setups
have exactly one Miqa MCP server connected — just use it. If more than one
is connected, ask the user which one they mean before proceeding.

This skill is often invoked as a follow-up to the `active-triggers` skill
(the user names a docker tag they saw in a sweep's Note or root-cause
cell), but stands on its own — it does not require having run a sweep
first, and doesn't assume any prior context about which triggers use the
version.

## Procedure

1. **Derive the Miqa web UI host, up front.** Read the `MIQA_SERVER_URL`
   env var backing the connected Miqa MCP server (e.g. a one-off
   `echo $MIQA_SERVER_URL`). If it matches `api.<env>.miqa.io` (starts with
   `api.`, ends with `.miqa.io`), the web host is `<env>.miqa.io` — strip
   the leading `api.`. If it doesn't match that shape, don't guess a web
   host at all. This host is only used for artifact links (step 8) and
   on-demand links given in the terminal reply — never as inline markdown
   links inside the terminal table itself (same rendering-bug rationale as
   the `active-triggers` skill: wide tables with inline `[text](url)`
   markup can silently collapse into a stacked block layout in this user's
   terminal).

2. **Resolve a fuzzy or relative version reference before searching, if the
   user didn't name an exact docker tag.** Phrasing like "the latest
   build", "the latest release build" (excluding drafts/snapshots/RCs), or
   "whatever's newest for demux" has no `version_value` to filter on yet.
   Call `list_test_chain_runs` with no version filter (newest-first,
   `limit` 30-50 is normally enough) and scan the returned `version_name`
   values for the newest one matching the criteria. There is no fixed,
   cross-deployment naming convention for what marks a draft/snapshot vs. a
   release build — infer it from the tag patterns actually present in this
   scan (e.g. a repeated marker like `-DRAFT-`, `-rc`, `-snapshot`, or a
   distinct registry path segment shared by the entries you're excluding),
   and if the scan doesn't make the pattern obvious, ask the user what
   distinguishes a release tag in their setup rather than guessing one.
   Extract the docker tag from the newest matching `version_name`
   (everything after the final `:`), state plainly in the reply which tag
   you resolved to and from which run/date, then proceed to step 3 with
   that tag. Don't guess silently — if nothing matches the criteria in the
   scan window, widen the limit before concluding there's no such build.

3. **Find every run for the version.** If the user gives a bare docker tag
   (no image path, e.g. `2.4.0-240102-a1b2c3d`) — or you resolved one in
   step 2 — call `list_test_chain_runs` with `version_field="docker_tag"`,
   `version_value="<tag>"`, and a generous `limit` (200-300 — the default
   100-run scan window can miss older matches; if the result comes back
   empty, widen further before concluding the version doesn't exist rather
   than assuming it's absent). This matches across every component/test
   chain in one call, which is what "all results" means here. Only reach
   for `find_test_chain_runs_by_version` instead if the user already gives
   you a full component-qualified display label (e.g.
   `acme/pipeline-a:2.4.0-240102-a1b2c3d`) — it only searches one
   component at a time, so it's the wrong tool when you don't yet know
   which components used that tag.

4. **Pull the per-check tally for each returned run that's actually done.**
   Check each run's `status` field from step 3 first — if it isn't
   `"done"` (e.g. `"Started"`), the run is still executing: don't call
   `get_test_chain_run_results` for it (the report may still be generating
   or the data may be incomplete), and don't guess pass/fail for it. For
   every run that is `"done"`, call `get_test_chain_run_results(run_id)`
   for all of them in parallel — these are independent lookups, batch them
   in one turn rather than firing them one at a time. Count PASS/WARN/FAIL
   from each result's **`check_status`, never `assertion_status`** — the
   two can disagree on the same row (observed directly: one run showed
   `assertion_status: "FAIL"` on a check whose `check_status` was
   `"PASS"`), so `check_status` is what drives the Checks-column tally.
   This tally is display detail only — it does not drive the row's Status
   (see step 5).

5. **Post a terminal table immediately** — don't dig into any failure
   before shipping this. Columns: Test Chain | Component | TCR | Checks |
   Status, one row per run, no inline links (per step 1's note). Since
   this terminal renders plain CommonMark (no cell background/text color),
   color both columns the same way the sibling `active-triggers` skill's
   terminal tables do: with a leading status emoji, never plain text alone.
   Status has three possible states, not two: 🔵 Running (still executing),
   🟢 Healthy, or 🔴 Failing (the latter two only apply once a run is
   `"done"`). For a still-running run (per step 4), skip the tally and show
   `— running` (or similar) in Checks and 🔵 Running in Status — before
   calling it stalled, sanity-check its elapsed time against how long this
   same test chain's other recent `"done"` runs took (same approach as
   `active-triggers` step 6); only call out a stall if it clearly exceeds
   that normal range, otherwise it's just "still running," not broken. For
   a `"done"` run, "Checks" is a compact tally with the fail/warn segments
   each prefixed by their emoji, e.g. `37/44 pass · 🔴 5 fail · 🟡 2 warn`
   (omit a segment entirely if its count is 0, don't show "🔴 0 fail").
   "Status" is 🟢 Healthy / 🔴 Failing, taken directly from that run's own
   `outcome` field (`list_test_chain_runs`/`find_test_chain_runs_by_version`
   already returned this in step 3 — pass → 🟢 Healthy, fail → 🔴 Failing).
   Don't synthesize Status from the WARN/FAIL tally: a run with
   `outcome: "pass"` stays 🟢 Healthy even if its checks include WARNs —
   the WARN count already surfaces in the Checks column (step 7 still
   applies, so it's never dropped), it just doesn't demote the row.

6. **Don't re-root-cause a failure that's already documented — but offer to.**
   If a run in the rollup is failing and it's the same signature already
   root-caused elsewhere (a prior `active-triggers` sweep, or an earlier
   rollup), name that plainly and cite the boundary TCR/build where it
   started — don't re-derive the full mechanism from scratch by default.
   After that summary, offer once to dig in fresh anyway (same offer
   pattern as the artifact offer in step 8: state it once, don't re-offer
   if they don't take it, don't start digging without a yes) — a
   previously-documented signature can still be worth re-checking (a fix
   landed and needs confirming, the "same signature" call itself might be
   wrong, etc.), so don't treat "already known" as a reason to foreclose
   the option. Do fresh root-cause digging immediately, without waiting for
   that offer to be taken, if the failure signature looks new instead
   (check this by comparing the failing check names and magnitudes against
   what was previously reported, not just by assuming "failing = same
   issue"). For fresh digging, the investigation steps are the same ones
   the `active-triggers` skill uses for a single trigger (pull
   `get_test_chain_run_environment` for the run and its likely boundary,
   distinguish content mismatch vs. baseline problem vs. execution crash,
   conclude into one of: real regression / needs-baseline-update /
   strict-threshold noise) — that skill's step 4 has the full detail if
   you need to reuse it.

7. **Never drop a WARN silently.** Always mention any WARN-status check
   found, even when the run's overall outcome is a pass — as a
   lower-priority note attached to that run's row/summary, not given equal
   billing with a FAIL.

8. **Artifact, on request only.** Don't publish unless the user asks —
   but after the terminal table, mention that a shareable, linked version
   is available (same offer pattern as `active-triggers`: state it once,
   don't re-offer if the user doesn't take it, don't publish without a
   yes). When they do ask, use `reference/template.html` (this skill's
   directory) as the literal starting file: copy it verbatim, only fill in
   the `{{PLACEHOLDER}}` tokens and repeated blocks, don't restyle or
   re-derive the palette/type/layout — it deliberately shares the exact
   design tokens (fonts, colors, chips, `.case`/`.proof` treatment) used by
   the sibling `active-triggers` skill's own `reference/template.html`, so
   a version rollup and a trigger sweep read as one family of reports. If
   that sibling template's tokens ever change, bring the change here too.

   - Masthead names the version tag itself as the page's subject (`<h1>`
     "Release Train" with the docker tag as a mono sub-line), not a
     trigger or sweep name.
   - The third stat tile is context-dependent: a clean build (no failing
     chains) uses tiles for chain count / checks executed / warnings; a
     build with any failing chain repurposes tile 2 for the failing-chain
     count (critical color) and folds the checks-executed figure into
     tile 3's label instead. Never color a 0 as critical.
   - One `.case` section per **failing** test chain (not per WARN — WARNs
     never get their own case, only the "Warnings on record" section).
   - Include the "Warnings on record" section whenever any run in the
     rollup carries a WARN, even if nothing failed outright; omit it only
     when there are zero WARNs anywhere in the rollup.
   - Unlike the terminal table, the artifact uses working links to
     `{web_host}/test_chain/{testchain_id}` and
     `{web_host}/test_chain_run/{tcr_id}` wherever step 1 derived a web
     host (plain text only if no web host could be derived, never a
     fabricated link).
   - Title names the version tag as a plain noun phrase (e.g.
     "2.4.0-240102-a1b2c3d Rollup"); favicon is always 🧬, matching
     `active-triggers`'s artifacts so both read as one family in a
     gallery of published reports.
   - Design history: this template was derived directly from two
     user-approved rollups —
     https://claude.ai/code/artifact/edc370f4-d4eb-436e-bf43-dae681c75126
     (clean build) and
     https://claude.ai/code/artifact/7c707dab-a212-4bb2-b276-9b4d5723a3d6
     (build with one failing chain) — treat those as the reference
     renders if the template's markup is ever ambiguous. If the user asks
     for a different look, ask whether to update `reference/template.html`
     (standing change, and consider whether the sibling sweep template
     should match) or just one-off it for this rollup.

## Notes

- This skill and `active-triggers` are siblings, not layers — either can
  be invoked without the other. Don't assume prior sweep context exists;
  if the user references "the same regression from the sweep" without
  you having that context in-conversation, ask which trigger/TCR they mean
  rather than guessing.
- If the version spans a very large number of test chains (dozens+), the
  same batching principle applies: fan out the `get_test_chain_run_results`
  calls in parallel rather than serially, and consider delegating to a
  `general-purpose` agent per batch if the raw data would otherwise flood
  the main context for low added value.
- Memory/prior-session notes about a version's status are a lead, never a
  citable fact — live data always wins. Re-verify against
  `get_test_chain_run_results` before repeating a "known failing" or
  "already fixed" characterization from memory.
