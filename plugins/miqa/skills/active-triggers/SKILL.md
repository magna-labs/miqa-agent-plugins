---
name: active-triggers
description: Use when the user asks "what's going on with my [most] active test triggers", "miqa trigger status", "why are my miqa triggers failing", or otherwise wants a status + root-cause sweep across Miqa test triggers (via a connected Miqa MCP server). Produces a fast pass/fail table first, then root-causes what's currently broken and offers to dig into anything that already recovered.
metadata:
  version: 1.10.0
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
   - Also derive the Miqa web UI host once, up front: read the
     `MIQA_SERVER_URL` env var backing the connected Miqa MCP server (e.g.
     a one-off `echo $MIQA_SERVER_URL`). If it matches `api.<env>.miqa.io`
     (starts with `api.`, ends with `.miqa.io`), the web host is
     `<env>.miqa.io` — strip the leading `api.`. If it doesn't match that
     shape (e.g. a raw gateway/Zuplo-style host with no `.miqa.io`
     suffix), don't guess a web host at all.
   - This host is used in two places only: the standing artifact template
     (step 6), which always renders real links, and on-demand TCR links
     (see step 3) — never as inline markdown links in the terminal tables
     themselves. Terminal tables (steps 3 and 6) always render trigger
     names and docker tags/TCR citations as **plain text**, even when a
     web host was derived — this was a deliberate change after the inline
     links rendered as messy raw `[text](url)` markup in this user's
     terminal rather than clean hyperlinks. Don't reintroduce inline
     table links; the artifact is the vehicle for clickable links.

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
     run's `id`/`run_id` (the TCR id), `outcome` (pass/fail), and `version_name`
     — capture these per active trigger for free, without any extra tool calls:
     the **latest run's outcome**, the **latest run's version + TCR id** (the
     docker tag is everything after the final `:` in `version_name`, dropping
     the registry/image path), and whatever **high-level pattern is visible across
     the pulled window itself**: **recovered** (failed earlier in the window,
     passing now — also note the date, version, and TCR id of that last
     failing run), **newly failing** (was passing, only the latest run failed
     — also note the date, version, and TCR id of that last passing run), or
     **intermittent** (flips pass/fail more than once in the window — not one
     clean transition). A window with no flip at all (monotonic pass or
     monotonic fail) has no pattern to report, just the current version. All
     of this feeds step 3's merged Status + Note directly, including the TCR
     ids cited (as plain text) in that Note.

3. **Post the quick status table immediately — before doing any root-cause
   digging.** The user wants to see what's green *first*; the "why did it
   fail last week" story is a follow-up, not the headline. Using only the
   latest-run outcome, version, and pattern captured in step 2 (no
   `get_test_chain_run_report` or `get_test_chain_run_environment` calls
   yet), post a three-column table, one row per active trigger:

   | Trigger | Status | Note |
   |---|---|---|
   | alpha-release | 🟢 Healthy | Passing on `1.2.0-260816-b8833cb` (TCR 60327), previously failing up to 2026-08-09 (`1.2.0-DRAFT-260809-c73ae0c`, TCR 60272) |
   | bravo-release | 🟢 Healthy | Intermittent — flips pass/fail across the window; currently on `1.2.0-260816-b8833cb` (TCR 60326) |
   | charlie-release | 🟢 Healthy | Passing on `1.2.0-260816-b8833cb` (TCR 60325) |
   | delta-release | 🔴 Failing | Failing on `1.2.0-DRAFT-260811-6e5c587` (TCR 60262), previously passing |

   Use 🟢 if the latest run passed, 🔴 if it failed, 🟡 if it's
   `incomplete`/`Started` (don't call this a stall yet — that's step 6). This
   table is a standalone deliverable — send it and stop before moving on to
   step 4, don't silently chain straight into root-causing.

   Trigger names and docker tags are always plain text in this table —
   never wrap them in markdown links (see step 1's note on why). The Note
   column always leads with a base clause naming what version the trigger
   is currently on: "Passing on `X`" or "Failing on `X`", using the bare
   docker tag (strip the registry/image path, e.g.
   `registry.example.com/company/pipeline-a:1.2.0-260816-b8833cb` →
   `1.2.0-260816-b8833cb`) so the cell stays narrow — but once stripped,
   never truncate or abbreviate the tag itself, same rule as step 6's
   root-cause table. Cite the TCR id in parentheses after the tag, e.g.
   "`X` (TCR NNNNN)", as plain text. Layer whatever pattern step 2 found
   on top of that base clause, don't replace it:
   - **recovered** — append ", previously failing up to {date of the last
     failing run} (`{that run's version}`, TCR {id})", e.g. "Passing on
     `X`, previously failing up to 2026-08-09 (`Y`, TCR NNNNN)".
   - **newly failing** — append ", previously passing"; add the last
     passing run's date/version too when it fits cleanly (e.g. "Failing
     on `X`, previously passing until 2026-08-11 (`Y`)"), but the bare
     ", previously passing" is fine on its own — step 4 pins the exact
     boundary anyway, this is just the headline.
   - **intermittent** — append "; flips pass/fail across the window"
     instead of a specific prior date/version, since there's no single
     clean boundary to cite.
   - **monotonic (no flip)** — no extra clause; the base "Passing on `X`"
     / "Failing on `X`" is the whole Note.

   If the user asks for a link to a specific trigger or TCR mentioned in
   the table (rather than the full artifact), give it on demand as a
   short plain list right below the table (e.g. "TCR 60327:
   {web_host}/test_chain_run/60327") — don't inline it back into the
   table, and don't proactively dump a links list unasked.

   This is still purely descriptive of the pulled window, not an
   explanation of *why* anything changed — keep it to one short sentence
   so the table stays narrow enough to render as real columns, and leave
   causation to steps 4/6. After the table, ask whether to dig into the
   root cause of any 🟢 trigger whose Note carries a recovered or
   intermittent pattern clause (not just the plain "Passing on `X`") —
   all of them, one in particular, or skip it. Do not start step 4's
   investigation on one of these until the user asks; a currently-green
   trigger is not an open problem, and unpacking its past pattern is
   optional context, not part of the core deliverable. A 🔴 "newly
   failing" trigger still goes straight to step 4 automatically like any
   other currently-broken trigger — the Note there is extra context, not
   a reason to hold off.

4. **Root-cause every active trigger that's currently broken — automatically,
   without asking.** A 🔴 or stalled 🟡 trigger from step 3 is a live,
   actionable problem, not optional follow-up, so proceed straight into this
   step for those. (Recovered 🟢 triggers only enter this step if the user
   asks for the dig-in offered in step 3 — see the scoping note there.)
   **Choose narration mode based on how many triggers need root-causing.**
   A backgrounded Agent call has no built-in way to stream interim
   progress — it only notifies once, at the very end. For a single
   trigger that reads as one long silent wait, even though the
   investigation itself has readable milestones (which check failed, what
   the diff showed, which boundary run is being checked next, the
   concluded bucket). Default to:
   - **Exactly 1 trigger:** investigate directly in the main thread
     yourself — call the tools inline rather than delegating to a
     backgrounded Agent, and narrate as you go: a short line after each
     milestone (e.g. "latest run fails on `<check>`, pulling the diff
     detail now", "diff is `<magnitude>` — checking whether that started
     here or earlier", "confirmed: baseline pointer didn't move, this is a
     real regression"). This is "thinking out loud" narration, not a
     status ping — each line should carry the actual finding so far, not
     just "still working." Finish with the same step 6 table either way.
   - **2 or more triggers:** fan out, but split each trigger's
     investigation into two checkpoint agent calls instead of one long
     silent one, so there's a narrated update partway through rather than
     a multi-minute void:
     - **Checkpoint 1 — diagnose:** one agent per trigger, in parallel,
       does the first two bullets below (find the failing check(s) on the
       latest run, pull diff detail) and returns just that preliminary
       finding — which check(s) failed, the diff magnitude, and whether
       it's a real value or only an aggregate match percentage. As each
       checkpoint-1 agent completes, post a one-line narration per
       trigger (e.g. "bravo-release: `Compare concordant bases` off by
       1.26% (~11.6B bases) — checking when this started").
     - **Checkpoint 2 — bucket:** once checkpoint 1 returns for a
       trigger, launch a second agent for that same trigger, seeded with
       checkpoint 1's finding, to do the remaining bullets below (pass→fail
       boundary, environment comparison, WARN check) and conclude the
       bucket. Feed its result into that trigger's row in step 6's table
       as it lands, using the same live-table/ping progress modes as
       before.
     - This costs one extra agent spin-up per trigger, traded for a
       narrated checkpoint instead of total silence. If the user has
       explicitly opted into multi-agent orchestration (e.g. asked for a
       workflow, or ultracode is on), prefer the `Workflow` tool's
       `log()` narrator lines and live progress tree instead of this
       manual two-checkpoint split — it's built for exactly this and
       gives finer-grained progress than two checkpoints. Don't reach for
       `Workflow` on your own initiative outside that opt-in.

   For each trigger being root-caused (whether investigated inline, via a
   checkpointed pair of agents, or in a single fanned-out agent), the steps
   are — checkpoint 1 covers the first two bullets, checkpoint 2 the rest,
   when split:
   - Pull `list_test_chain_runs_for_trigger(trigger_id, limit=30)` and find the exact pass→fail
     boundary (or confirm it's been failing the whole window).
   - **Batch every independent lookup into one round trip instead of firing
     them one at a time.** Once you have the run_ids you need (latest
     failing, boundary, prior-pass), issue all of that trigger's
     `get_test_chain_run_results` / `get_test_chain_run_environment` /
     `get_test_chain_run_report` calls together as parallel tool calls in
     the same turn rather than sequentially — none of them depend on each
     other, only on IDs you already have. This cuts real wall-clock time
     (measured ~1.5-3x depending on how many calls are batched); it doesn't
     need its own explanation in the final report, just do it.
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
   - **Don't assume failures on different checks or different test blocks
     within the same trigger are separate root causes — check whether they
     reconcile to one cause first.** Two (or more) checks failing at the
     same pass→fail boundary run is a signal they may be the *same*
     underlying change surfacing twice, not automatically two bucket
     labels. Before filing a combined 🔴+🟡 (or any two-bucket) verdict,
     pull the actual per-record diff detail for *each* failing check (not
     just the headline metric) and check whether they reconcile — e.g. a
     new metric appearing in one test block's diff table, and a matching
     drop in another block's numbers, that sum to the same value. Only
     split into two distinct root causes once the evidence (different
     boundary runs, or diffs that don't reconcile) actually shows two
     separate mechanisms. Defaulting to "different check name or test
     block = different cause" without checking is how one regression gets
     mis-reported as a regression plus an unrelated chronic issue.
   - **Live data always overrides memory or a prior sweep's notes — treat
     anything remembered about a trigger as a hypothesis to re-verify, not
     a fact to repeat.** A stored note that a check has a "long-standing"
     or "known" issue describes a state that can have changed since it was
     written (rebaselined, regressed again, fixed, recurred with a
     different cause). Before reusing any characterization from memory —
     especially words like "long-standing," "chronic," "known issue," or
     an old bucket label — pull the actual last-known-good run for *this*
     sweep (`get_test_chain_run_results` on the boundary TCR) and confirm
     the claim still holds against what's live right now. If what you find
     live contradicts memory, live data wins, full stop — report what you
     just verified, then correct the stored memory afterward so it doesn't
     mislead the next sweep too.
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
   - Conclude explicitly, into one of three buckets — these need different
     owners to act on, so don't collapse them:
     - **real product regression** — code/model/CLI output actually changed
       and content now differs from a *correct* baseline; needs an
       engineering fix. If the team later confirms the new behavior is
       intentional, the eventual fix is a rebaseline — but that
       confirmation hasn't happened yet, so report it as a regression, not
       as "needs baseline update", until it has.
     - **needs a baseline update** — reserved for cases where the baseline
       *itself* is demonstrably the problem right now: its pointer is
       frozen/stale, it was swapped to an incompatible comparison version,
       or its stored output files were deleted/moved. The tell: the run
       would pass today against a different, current baseline. Don't apply
       this label just because a past instance of the same trigger was
       once fixed by rebaselining, or because an unconfirmed regression
       *might* end in a rebaseline later — that's still bucket one.
     - **strict-threshold noise** — the run's content and the baseline are
       both fine; the check enforces a zero/near-zero tolerance (e.g.
       `pct_diff_threshold: 0`), so it fails on any nonzero diff, including
       ordinary floating-point/measurement noise. A strict tolerance is not
       automatically a bug — it may be an intentional choice by the check
       owner. Describe it as that ("strict by design, failing on
       noise-level diffs") rather than calling it "misconfigured" or
       something that "needs" fixing; noting that widening the threshold
       is an option is fine, but leave the decision to the check owner.
   - **Never assign a bucket from a check's configuration alone.** A
     strict threshold visible in `get_test_chain_run_environment`'s
     `assertions` block only tells you the check would fail on any nonzero
     diff — not how big the actual diff is. Always pull the actual failing
     value from `get_test_chain_run_report` (expected vs. actual, not just
     the threshold field) and confirm the mismatch is genuinely
     noise-sized — roughly the 5th+ significant digit, not a swing
     measured in whole percent or in thousands/millions/billions of units
     — before calling it strict-threshold noise. A zero-tolerance check
     failing on a multi-percent or multi-unit swing is real signal
     tripping a strict check, not proof the check is miscalibrated —
     that's bucket one or two. When the diff magnitude can't be determined
     at all (no field/record-level breakdown is available, see below),
     default to reporting an unconfirmed regression instead — the safer
     bucket to be wrong toward.
   - **Whenever a check's diff detail doesn't expose field- or
     record-level granularity, that's an API limitation, not a sign the
     check is uninteresting — this isn't specific to any one check_type
     or result shape.** `get_test_chain_run_report`'s own docs note the
     detail field's shape varies by check_type (`diff_details_raw`,
     `result`, a table's `table_items`, etc.) — inspect the specific
     assertion rather than assuming one field name or one coarse-only
     pattern (e.g. an aggregate match percentage with empty
     `diff_indexes`/`diffs`) is the only way this shows up. Whatever form
     it takes for that check_type, if what comes back is a summary/count/
     percentage rather than the actual differing value(s), treat it the
     same way. `inspect_execution_outputs` can't fill the gap either: by
     design it returns only column headers/types, never actual data
     values. Don't silently drop or skip such a check because "there's
     nothing to show" — report the coarser diff you did see and say
     explicitly that the specific differing field/metric isn't
     retrievable through the connected tools, so a human would need to
     open the actual output file (e.g. via the Miqa web UI) to identify
     it.
   - **WARN-status checks are a different severity from FAIL, not a
     different category of "ignore."** When pulling `get_test_chain_run_results`
     for the run being root-caused, note any `check_status: "WARN"` entries
     alongside the FAILs, even though a WARN alone doesn't flip the run's
     overall outcome. Always flag a WARN you find — never drop it silently
     — but always report it as secondary to whatever FAIL is the actual
     root cause: it doesn't get its own 🔴/🟡 status chip or equal billing,
     it's a "found this too, lower priority" note attached to the main
     finding (see step 6 for exactly how that's presented in each output
     format).

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
   later deliverable from the quick three-column table in step 3, scoped only
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
   | bravo-release | 🔴 Real regression | CLI flag renamed `--input-mode`→`--mode`, crashing since TCR 60301 (`1.2.0-DRAFT-260811-6e5c587`) |
   | charlie-release | 🟡 Needs baseline update | `@release_series` baseline frozen since TCR 59905, "no comparison version found" |
   | delta-release | 🟢 Healthy, still running | TCR 60304 within normal ~10.5h runtime, not stalled |
   | alpha-release | 🟢 Recovered | `@release_series` baseline pointer broken (TCR 60238–60272); admin repointed baseline + force-rebaselined history on TCR 60278; current runs pass organically |

   Use 🔴 for a real product regression, 🟡 for either "needs a baseline
   update" (stale/frozen baseline pointer, comparison version swapped to
   something incompatible, or baseline files deleted — the baseline itself
   is the problem right now) or "strict-threshold noise" (the check enforces
   a zero/near-zero tolerance and is failing on noise-level diffs — describe
   it that way rather than calling the check "misconfigured"; the strict
   tolerance may well be intentional) — name which of the two it is
   explicitly in the cell text rather than defaulting both to "needs
   baseline update"; they point to different owners (test-config/baseline
   owner vs. whoever owns the check's threshold). 🟢 for healthy/passing/still-running-normally
   (including "Recovered" — currently passing, dug into on request after
   having failed earlier in the window). Don't downgrade an unconfirmed
   content regression to 🟡 just because a rebaseline is the likely
   eventual fix — keep it 🔴 until the team confirms the new behavior is
   intentional; see step 4's three-bucket breakdown.
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
   tag down to just the TCR number. Trigger names and "TCR NNNNN"
   citations are always plain text in this table too, same as step 3 —
   give a link only if the user asks for one (see step 3's on-demand
   note). Aim for roughly one sentence
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

   **A WARN-level finding is not a second root cause — never give it its
   own status emoji or equal billing with a FAIL.** It's a lower-priority
   footnote to whatever FAIL is the actual Status/root cause, but it must
   still be mentioned, never dropped for tidiness. Append it to the end of
   the cell as a clearly demoted clause, e.g. "; also WARNs on `<check
   name>` (14.3% aggregate diff, field-level detail not available via the
   API)" — no separate emoji, no bold sub-heading, no combined-chip
   treatment like the two-FAIL case above. This keeps the banner reading
   as one clear severity while still surfacing the WARN for whoever wants
   to dig further.

   Output this as a plain markdown table directly in the chat response —
   do not publish it as an Artifact (or any other rendered/exported
   format) unless the user asks for that. A terminal-rendered markdown
   table is the expected deliverable for this skill.

   After the table, add one short closing line offering the rendered
   version too — and since the terminal tables are plain text with no
   inline links, this is also where clickable links actually live, so say
   so: e.g. "Want the interactive version — clickable links to every
   trigger and run — as a shareable report? I can publish it." Don't
   guess or assume interest, just surface the option so the user doesn't
   have to already know an Artifact version exists in order to ask for
   it. Don't publish anything unless they say yes; if they don't respond
   to the offer or move on to something else, drop it, don't re-offer on
   a later sweep in the same conversation.

   **If the user asks for an Artifact, rendered report, or HTML
   version** (up front, as a follow-up after seeing the terminal table, or
   by accepting the offer above): publish an HTML artifact summarizing the
   same findings — this is additive, not a replacement for the terminal
   deliverable above, which still gets sent first/regardless. Reuse the
   fixed design system below verbatim rather than running a fresh
   `artifact-design` pass each time — the point is that repeat sweeps look
   like the same report, not a redesign per run. Only fall back to
   `artifact-design` if the user asks for a different look, in which case
   ask whether to update this standing template or just one-off it.

   **Standing design system for this skill's artifacts:**
   - **Use `reference/template.html` (in this skill's directory) as the
     literal starting file.** Copy its content verbatim into your working
     file, then only replace the `{{PLACEHOLDER}}` tokens and fill in the
     repeated blocks (status-table rows, one root-cause `<section>` per
     broken trigger) with this sweep's data. Do not restyle, do not
     re-derive the palette/type/layout from scratch, do not invent new
     components — the point of a fixed template file (rather than a prose
     description) is that repeat sweeps are byte-for-byte the same design,
     not a redesign-by-memory each time.
   - **Fonts**: Archivo for headings/numerals, Source Serif 4 for body
     prose, IBM Plex Mono for every docker tag, TCR id, timestamp, chip,
     and table header label — all wired up already in the template's
     `<link>` and `<style>`.
   - **Palette**: warm paper background, teal accent, IBM-Plex-Mono chips
     for status (`.chip.healthy` / `.chip.failing` / `.chip.warn`), full
     light/dark tokens — all defined in the template's `:root` blocks, see
     that file for exact values. Don't hand-roll new colors.
   - **Layout** — same structure every time, only the content changes: a
     masthead (eyebrow, `<h1>` naming the sweep + date, mono meta strip
     with window/scope/host); a 3-up stat-tile row; the step-3 status
     table (status chip + mono tag/TCR links); one "Root Cause —
     `{trigger}`" section per broken trigger, each a `.case` card. Within a
     case, use the template's optional `.boundary` three-point timeline
     when there's a clean single pass→fail boundary worth visualizing, a
     `.proof` block only when the root cause involves a numeric
     reconciliation worth showing as a receipt (don't force one when there
     isn't one), and `.aside` for anything lower-priority than the case's
     main FAIL narrative: a second, unrelated FAIL-level issue on the same
     trigger (state explicitly which of step 4's three buckets — regression
     / needs-baseline-update / strict-threshold-noise — it belongs to, don't fold it
     into the main narrative's diagnosis), and separately, any WARN-status
     finding uncovered while root-causing (see step 6's "WARN is not a
     second root cause" rule) — always flagged, never given the main case's
     `<h3>`/`.boundary`/`.proof` treatment, always read as a footnote. A
     plain mono footer with host + sweep date closes the page.
   - **Title & favicon** — title names the sweep as a plain noun phrase,
     no dash-appended explainer (e.g. "August 25 Trigger Sweep", not
     "Trigger Health — Aug 25"); favicon is always 🧬.
   - **Design history**: an earlier version of this template used a
     different card/chip treatment and (wrongly) filed a strict-threshold-noise
     issue under a "needs baseline update" chip. The user explicitly preferred
     the version now captured in `reference/template.html` (published at
     https://claude.ai/code/artifact/6b4c2484-ada8-4dee-8654-13bc8a993d24)
     over that earlier one — this is the locked version going forward. If
     the user asks for a different look in the future, ask whether to
     update `reference/template.html` (standing change) or just one-off it
     for this sweep, and if they confirm a standing change, edit the
     template file itself so it stays the single source of truth.

   The terminal table's ~25-30 word cap on Note/Root-cause cells exists
   only to dodge a specific terminal-renderer bug (wide tables silently
   collapsing into a stacked block layout — see step 6's "why cell length
   matters" note); it does not apply to the artifact, which isn't a
   markdown table and can't collapse that way. Root-cause cells in the
   HTML version may run notably longer than the terminal cap — enough to
   fully explain the mechanism (e.g. carry the arithmetic reconciliation,
   name both the earlier and later failure signature on a two-issue
   trigger, quote the actual log line) rather than compressing it to a
   single headline sentence. To keep a longer cell from overwhelming the
   table visually, drop its font-size a step below the surrounding body
   text and give it a touch more line-height, rather than shortening the
   content — table proportions are a layout problem to solve with type
   size, not a reason to cut real findings. This is not license to pad
   with filler, throat-clearing, or restating the Status column in prose:
   every extra sentence should be information the terminal cell had to
   drop for space, not new wordiness for its own sake. Never thin out
   root-cause text to make the layout prettier in the other direction
   either — the full-docker-tag, never-drop-a-second-failure-mode rules
   from the terminal table still apply verbatim, this is strictly an
   allowance for more, not less. Unlike the terminal tables, the artifact
   should use working links to `{web_host}/test_trigger/{trigger_id}` and
   `{web_host}/test_chain_run/{tcr_id}` wherever step 1 derived a web host
   (plain text only if no web host could be derived, never a fabricated
   link) — the artifact is the intended home for clickable links in this
   skill. When re-running this skill as a follow-up ask, publish a new
   artifact rather than trying to update a prior one from a different
   conversation, unless the user names an existing artifact URL to
   redeploy.

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
- **Memory/prior-session notes are a lead, never a citable fact — live data
  always wins.** See step 4's two bullets on this: re-verify the boundary
  run live before repeating any "long-standing"/"known issue" framing from
  memory, and reconcile diffs across failing checks/test blocks before
  splitting one trigger into two bucket labels.
