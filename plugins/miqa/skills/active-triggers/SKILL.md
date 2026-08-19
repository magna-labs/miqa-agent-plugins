---
name: active-triggers
description: Use when the user asks "what's going on with my [most] active test triggers", "miqa trigger status", "why are my miqa triggers failing", or otherwise wants a status + root-cause sweep across Miqa test triggers (via a connected Miqa MCP server). Produces a fast pass/fail table first, then root-causes what's currently broken and offers to dig into anything that already recovered.
metadata:
  version: 1.2.0
---

# Miqa Active Trigger Triage

Sweeps every enabled Miqa TestTrigger, finds which ones are actually running
(not just enabled-but-dormant), and root-causes any that are failing —
distinguishing real product regressions from stale test config (baselines
that need updating, comparison versions that never got re-anchored) and
from pipelines that are simply still executing.

This skill calls tools named `list_test_triggers`, `list_test_chain_runs_for_trigger`,
`get_test_chain_run_report`, and `get_test_chain_run_environment` on whichever Miqa MCP
server is connected (tool names follow the pattern
`mcp__<server-name>__<tool>`). Most setups have exactly one Miqa MCP server
connected — just use it. If more than one is connected (e.g. separate
servers per environment), ask the user which one they mean before running
the sweep, rather than guessing from the server name.

## Procedure

1. **List and filter.** Call `list_test_triggers`. Keep only `disabled: false`
   entries — never spend budget investigating disabled triggers.

2. **Find which enabled triggers are actually active.** "Enabled" and
   "recently running" are different things — triggers can sit enabled but
   dormant for months or years. For each enabled trigger, call
   `list_test_chain_runs_for_trigger(trigger_id, limit=15)` and check the most recent run
   date. A trigger counts as **active** if it has run more than once in the
   last 14 days (adjust the window if the user asks for a different one, or
   if cadences in this fleet run slower than daily).
   - This step is naturally parallelizable: batch the enabled triggers into
     groups of ~10-15 and fan out `general-purpose` agents (via the Agent
     tool) to pull `list_test_chain_runs_for_trigger` for each batch and report back a
     compact table (id, name, run count, most recent date, cadence, last 3
     outcomes, ACTIVE flag). Don't do this serially in the main context —
     it burns a lot of tokens for low-value raw data.
   - This same `list_test_chain_runs_for_trigger(limit=15)` pull already carries each
     run's `outcome` (pass/fail) — capture two things from it per active trigger
     for free, without any extra tool calls: the **latest run's outcome**, and
     whether **any run in the pulled window failed** even if the latest passed
     (call this "recovered"). Both feed step 3 directly.

3. **Post the quick status table immediately — before doing any root-cause
   digging.** The user wants to see what's green *first*; the "why did it
   fail last week" story is a follow-up, not the headline. Using only the
   latest-run outcome captured in step 2 (no `get_test_chain_run_report` or
   `get_test_chain_run_environment` calls yet), post a three-column table, one
   row per active trigger:

   | Trigger | Status | Note |
   |---|---|---|
   | demux-release | 🟢 Healthy | Failed earlier this week, now recovered |
   | gdc-str-release | 🟢 Healthy | Failed earlier this week, now recovered |
   | rc-release | 🟢 Healthy | — |
   | ssvc-tn-release | 🔴 Failing | — |

   Use 🟢 if the latest run passed, 🔴 if it failed, 🟡 if it's
   `incomplete`/`Started` (don't call this a stall yet — that's step 6). This
   table is a standalone deliverable — send it and stop before moving on to
   step 4, don't silently chain straight into root-causing.

   The Note column is where step 2's "recovered" flag surfaces — still no
   explanation of *why* yet, just the fact, inline on that trigger's own row
   rather than as separate prose below the table. Leave it `—` for triggers
   that didn't flip during the window. Keep this table at the same high
   level as before (recovered fact only, not a root cause); the extra
   column doesn't turn step 3 into step 6's deep-dive. After the table, ask
   whether to dig into the root cause of the recovered ones — all of them,
   one in particular, or skip it. Do not start step 4's investigation on a
   recovered trigger until the user asks; a currently-green trigger is not an
   open problem, and unpacking why it used to fail is optional context, not
   part of the core deliverable.

4. **Root-cause every active trigger that's currently broken — automatically,
   without asking.** A 🔴 or stalled 🟡 trigger from step 3 is a live,
   actionable problem, not optional follow-up, so proceed straight into this
   step for those. (Recovered 🟢 triggers only enter this step if the user
   asks for the dig-in offered in step 3 — see the scoping note there.)
   For each trigger being root-caused, fan out one root-cause agent per
   trigger (in parallel) with instructions to:
   - Pull `list_test_chain_runs_for_trigger(trigger_id, limit=30)` and find the exact pass→fail
     boundary (or confirm it's been failing the whole window).
   - On the latest failing run, call `get_test_chain_run_report` for per-check
     diff detail — don't stop at pass/fail. Distinguish: genuine content
     mismatch vs. "missing matching file"/`missing_in_baseline: true`
     (baseline needs updating) vs. execution failure (crash/exit code, check
     `execution_failure` in `get_test_chain_run_environment` — **not**
     `get_test_chain_run_sample_metadata`, whose schema is per-chain and often
     doesn't carry execution status at all).
     `get_test_chain_run_report`'s payload is frequently 700K+ chars — it's
     usually saved to a file rather than returned inline. Don't try to
     read it whole; narrow to the specific failing `check_name`(s) first
     (from `get_test_chain_run_results`) and jq/grep into the saved file for
     just those.
   - **For execution failures, don't stop at `exit_code`/`status_reason`** —
     those are usually just generic harness-level boilerplate (e.g.
     "Essential container in task exited" says nothing about *why*). Scan
     the `execution_failure.log_tail` entries for the actual
     application-level error line — look near the end, for message text
     containing things like `[E]`, `Error`, `Exception`, `Traceback`,
     `fatal`, `required`, `failed to` — and quote that specific message
     (e.g. a missing/renamed CLI flag, a model/feature-schema mismatch, an
     assertion string) in the report. A category label like "container
     crashed" or "exit code 1" alone is not sufficient root cause.
   - Compare `get_test_chain_run_environment` across the pass/fail boundary —
     did the baseline pointer change (`default_baseline_tbr_id`), did the
     docker tag/version change, or did nothing external change (pointing to
     a genuine code regression)? For `missing_in_baseline`/"no comparison
     version found" errors specifically, check whether the run is
     comparing against the *same* baseline identifier that past
     (previously-passing) runs used. Same baseline ID, newly broken →
     the baseline's own output files were likely deleted/moved — flag as
     urgent test-infra breakage. Different/new baseline (e.g. a draft
     workflow version with no prior successful run) → it never had a
     baseline yet, which is a lower-urgency "not anchored" situation, not
     a deletion.
   - **Don't assume the failure signature is uniform across a long failing
     streak.** A trigger that's been failing for weeks can silently change
     *why* it's failing partway through (e.g. a content/assertion mismatch
     for a month, then a CLI crash stacks on top starting a few days ago).
     Checking only the latest failing run and backdating that signature to
     the whole window is wrong. Pull `get_test_chain_run_environment` for BOTH
     the earliest failing run in the streak AND the latest, and compare
     `execution_status` (`"Done"` = assertion/content-level failure —
     check `latest_status_event`/assertion detail; `"Failed"` = execution
     crash — check `execution_failure`) plus the actual error at each end.
     If they differ, that's two distinct issues with two distinct start
     dates — report both explicitly (e.g. "content mismatch since TCR
     X; a separate execution crash started additionally on TCR Y"), don't
     collapse them into one story dated to the older boundary.
   - **When checking that earliest failing run, an empty/null
     `execution_failure` (status/exit_code/log_stream_name all null,
     `log_tail: []`) does NOT mean nothing crashed.** AWS log retention
     means genuinely-crashed older executions can lose their log data
     over time — the absence is expected on old runs, not a Miqa gap or
     proof it was a clean assertion failure. Don't conclude "no crash
     here" from an empty `execution_failure` alone on an old run; check
     `latest_status_event`/`execution_status` too, and lean on the most
     recent failing run (whose logs should still be live) for the
     detailed signature.
   - Conclude explicitly: **real product regression** (code/model/CLI
     changed and broke something, needs an engineering fix) vs. **needs a
     baseline update** (baseline is stale/frozen or was swapped to something
     incompatible — the owner just needs to rebaseline/re-anchor the
     comparison version) — these need different owners to act on.

5. **Before calling anything "stuck": check the runtime baseline.** If a run
   shows status `incomplete`/`Started` with `execution_end == execution_start`
   or missing, do NOT conclude it's stalled. First pull
   `get_test_chain_run_environment` for 1-2 prior *successful* runs of that same
   test chain and note their `execution_start`→`execution_end` duration. If
   elapsed real time since the incomplete run's start is still within that
   normal runtime range, it's simply still executing — report it as healthy
   and still-running, not broken. Only flag a real stall if elapsed time
   clearly exceeds the normal runtime for that chain.

6. **Report progress while step 4 is running, then the final result, as an
   actual markdown table** — not a bulleted list of per-trigger paragraphs.
   This is the deep-dive table (Trigger, Status, Root cause) — a separate,
   later deliverable from the quick two-column table in step 3, scoped only
   to whatever triggers actually entered step 4 (the currently-broken ones,
   plus any recovered ones the user asked to dig into).

   **Progress mode while root-cause agents (step 4) are still in flight:**
   - **Fewer than 10 triggers being root-caused:** default to **live table**
     mode. As soon as step 4 kicks off, post the full table pre-seeded with
     one row per trigger entering step 4, in a stable order (e.g. alphabetical
     by trigger name) — unresolved rows show Status `⏳ pending` and Root cause
     `—`. Each time a root-cause agent completes, reprint the whole table
     with that row filled in. The table update *is* the progress update —
     don't also add separate narrative pings on top of it.
   - **10 or more triggers being root-caused:** default to **ping mode** — a
     brief one-line status per completion (trigger name + status emoji +
     one-clause finding) as each agent lands, holding the full table for the
     end. Reprinting a table with 10+ pending rows on every completion adds
     more noise than it saves.
   - **Escalation:** if ping mode is active and more than 60 seconds pass
     without every root-cause agent completing, switch to live table mode
     for the remainder of the sweep — post the table now (completed rows
     filled in, remaining rows `⏳ pending`) and keep updating it as
     further results land. Switch automatically; don't stop to ask the user
     first.

   One row per trigger that entered step 4, three columns:

   | Trigger | Status | Root cause |
   |---|---|---|
   | gdc-str-release | 🔴 Real regression | CLI flag renamed `--bam-input`→`--bam`, crashing since TCR 60301 (`1.2.0-DRAFT-260811-6e5c587`) |
   | rc-release | 🟡 Needs baseline update | `@release_series` baseline frozen since TCR 59905, "no comparison version found" |
   | ssvc-tn-release | 🟢 Healthy, still running | TCR 60304 within normal ~10.5h runtime, not stalled |
   | demux-release | 🟢 Recovered | `@release_series` baseline pointer broken (TCR 60238–60272); admin repointed baseline + force-rebaselined history on TCR 60278; current runs pass organically |

   Use 🔴 for a real product regression, 🟡 for "needs a baseline update"
   (stale baseline, frozen/un-re-anchored comparison version, etc. — an
   action item for whoever owns the test config, not a code bug), 🟢 for
   healthy/passing/still-running-normally (including "Recovered" — currently
   passing, dug into on request after having failed earlier in the window).
   For a forced-rebaseline recovery specifically, check whether the *current*
   runs resolve their baseline and pass organically (`forced: false` in the
   latest `get_test_chain_run_environment`) — a bulk `forced: true` "Mark pass"
   rebaseline event on the historical failing runs only cleans up the record;
   it doesn't by itself prove the underlying issue (e.g. a baseline pointer)
   was actually fixed going forward. Each root-cause cell should name
   **the actual underlying error** (the specific exception/log message, the
   renamed/missing flag, the model-schema mismatch — not a generic label
   like "crashed" or "exit code 1") and always cite the **full docker tag +
   TCR ID** (e.g. `1.2.0-260730-7d6e54f`, TCR 60298), not the internal
   `version_identifier` name like `v0.0.130` — never abbreviate the docker
   tag down to just the TCR number. Aim for roughly one sentence
   (~25-30 words) when there's a single root cause; the cell wraps onto
   multiple lines in a properly-rendered table, that's fine and expected.
   If a trigger genuinely has two distinct root causes (e.g. a stale
   baseline plus a separate later regression), it's fine for the cell to
   run longer to cover both (combine status emoji too, e.g. 🔴+🟡) — that's
   important information, don't drop or bury the second one. Only if a
   cell truly can't fit both without becoming unreadable, name the more
   urgent one in the cell and add a note flagging that there's a second,
   distinct failure mode on that trigger worth a follow-up look — don't
   silently omit it. Do not restate the same information again as prose
   paragraphs below the table — the table is the deliverable; a
   one-sentence lead-in and closing note are enough surrounding text.

   Output this as a plain markdown table directly in the chat response —
   do not publish it as an Artifact (or any other rendered/exported
   format) unless the user explicitly asks for that. A terminal-rendered
   markdown table is the expected deliverable for this skill.

   **Why cell length matters here, specifically:** some terminal markdown
   renderers silently fall back to a stacked "**Trigger:** x /
   **Status:** y / **Root cause:** z" block-per-row layout — visually
   indistinguishable from a bulleted list — when a table's *total* width
   (summed across all three columns, accounting for the longest cell in
   each) is too wide, even though the markdown itself is valid
   `| a | b | c |` syntax. Short 2-4 word Trigger/Status cells plus a
   ~25-30 word Root cause cell is the calibrated size that reliably renders
   as real columns. If a table you send ever collapses into that stacked
   look, trim filler next time (shorter trigger names, tighter phrasing) —
   but that trimming budget never comes from dropping a real second failure
   mode or shortening a docker tag.

## Notes

- Always ship the quick status table (step 3) before any root-causing. It
  should be fast — it's built entirely from data step 2 already pulled, no
  extra tool calls. Don't let step 4's investigation delay it.
- Don't auto-deep-dive a trigger just because it failed at some point in the
  last 14 days — only currently-broken (🔴/stalled 🟡) triggers get automatic
  root-cause. A trigger that's green right now but failed earlier gets a
  one-line hint and an offer, not an automatic investigation.
- If the trigger count is large (dozens+), the two-phase fan-out (scan for
  activity, then root-cause only the currently-failing/incomplete ones) keeps
  this fast and cheap instead of root-causing everything indiscriminately.
