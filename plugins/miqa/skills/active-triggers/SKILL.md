---
name: active-triggers
description: Use when the user asks "what's going on with my [most] active test triggers", "miqa trigger status", "why are my miqa triggers failing", or otherwise wants a status + root-cause sweep across Miqa test triggers (via a connected Miqa MCP server). Produces a final table of trigger, status, and root cause.
metadata:
  version: 1.0.1
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

3. **Root-cause every active trigger that isn't clean.** For each active
   trigger with recent failures, fan out one root-cause agent per trigger
   (in parallel) with instructions to:
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

4. **Before calling anything "stuck": check the runtime baseline.** If a run
   shows status `incomplete`/`Started` with `execution_end == execution_start`
   or missing, do NOT conclude it's stalled. First pull
   `get_test_chain_run_environment` for 1-2 prior *successful* runs of that same
   test chain and note their `execution_start`→`execution_end` duration. If
   elapsed real time since the incomplete run's start is still within that
   normal runtime range, it's simply still executing — report it as healthy
   and still-running, not broken. Only flag a real stall if elapsed time
   clearly exceeds the normal runtime for that chain.

5. **Report progress while step 3 is running, then the final result, as an
   actual markdown table** — not a bulleted list of per-trigger paragraphs.

   **Progress mode while root-cause agents (step 3) are still in flight:**
   - **Fewer than 10 triggers being root-caused:** default to **live table**
     mode. As soon as step 3 kicks off, post the full table pre-seeded with
     one row per active trigger, in a stable order (e.g. alphabetical by
     trigger name) — unresolved rows show Status `⏳ pending` and Root cause
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

   One row per active trigger, three columns:

   | Trigger | Status | Root cause |
   |---|---|---|
   | gdc-str-release | 🔴 Real regression | CLI flag renamed `--bam-input`→`--bam`, crashing since TCR 60301 (`1.2.0-DRAFT-260811-6e5c587`) |
   | rc-release | 🟡 Needs baseline update | `@release_series` baseline frozen since TCR 59905, "no comparison version found" |
   | ssvc-tn-release | 🟢 Healthy, still running | TCR 60304 within normal ~10.5h runtime, not stalled |

   Use 🔴 for a real product regression, 🟡 for "needs a baseline update"
   (stale baseline, frozen/un-re-anchored comparison version, etc. — an
   action item for whoever owns the test config, not a code bug), 🟢 for
   healthy/passing/still-running-normally. Each root-cause cell should name
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

- Don't bother deep-diving triggers that are active and passing cleanly —
  just note them as healthy.
- If the trigger count is large (dozens+), the two-phase fan-out (scan for
  activity, then root-cause only the failing/incomplete ones) keeps this
  fast and cheap instead of root-causing everything indiscriminately.
