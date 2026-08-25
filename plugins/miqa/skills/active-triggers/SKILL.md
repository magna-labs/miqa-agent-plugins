---
name: active-triggers
description: Use when the user asks "what's going on with my [most] active test triggers", "miqa trigger status", "why are my miqa triggers failing", or otherwise wants a status + root-cause sweep across Miqa test triggers (via a connected Miqa MCP server). Produces a fast pass/fail table first, then root-causes what's currently broken and offers to dig into anything that already recovered.
metadata:
  version: 1.6.1
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
   - Also derive the Miqa web UI host once, up front, so trigger names and
     docker tags can be posted as clickable links for the rest of this
     sweep (steps 3 and 6): read the `MIQA_SERVER_URL` env var backing the
     connected Miqa MCP server (e.g. a one-off `echo $MIQA_SERVER_URL`).
     If it matches `api.<env>.miqa.io` (starts with `api.`, ends with
     `.miqa.io`), the web host is `<env>.miqa.io` — strip the leading
     `api.`. If it doesn't match that shape (e.g. a raw gateway/Zuplo-style
     host with no `.miqa.io` suffix), don't guess a web host — render
     trigger names and version tags as plain text for the rest of the
     sweep, never fabricate a link. When a web host is available: a
     trigger name links to `{web_host}/test_trigger/{trigger_id}`; a
     specific run/version citation links to
     `{web_host}/test_chain_run/{tcr_id}`. Terminal markdown renderers
     measure table column width by the link's *visible text*, not the
     underlying URL, so wrapping names/tags in links doesn't change any of
     the cell-width guidance below.

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
     ids used to link tags per step 1's host-derivation note.

3. **Post the quick status table immediately — before doing any root-cause
   digging.** The user wants to see what's green *first*; the "why did it
   fail last week" story is a follow-up, not the headline. Using only the
   latest-run outcome, version, and pattern captured in step 2 (no
   `get_test_chain_run_report` or `get_test_chain_run_environment` calls
   yet), post a three-column table, one row per active trigger:

   | Trigger | Status | Note |
   |---|---|---|
   | [demux-release](https://{web_host}/test_trigger/525aae1b) | 🟢 Healthy | Passing on [`1.2.0-260816-b8833cb`](https://{web_host}/test_chain_run/60327), previously failing up to 2026-08-09 ([`1.2.0-DRAFT-260809-c73ae0c`](https://{web_host}/test_chain_run/60272)) |
   | [gdc-str-release](https://{web_host}/test_trigger/fb8e25c4) | 🟢 Healthy | Intermittent — flips pass/fail across the window; currently on [`1.2.0-260816-b8833cb`](https://{web_host}/test_chain_run/60326) |
   | [rc-release](https://{web_host}/test_trigger/46f9b657) | 🟢 Healthy | Passing on [`1.2.0-260816-b8833cb`](https://{web_host}/test_chain_run/60325) |
   | [ssvc-tn-release](https://{web_host}/test_trigger/54157ec2) | 🔴 Failing | Failing on [`1.2.0-DRAFT-260811-6e5c587`](https://{web_host}/test_chain_run/60262), previously passing |

   Use 🟢 if the latest run passed, 🔴 if it failed, 🟡 if it's
   `incomplete`/`Started` (don't call this a stall yet — that's step 6). This
   table is a standalone deliverable — send it and stop before moving on to
   step 4, don't silently chain straight into root-causing.

   Trigger names link to `{web_host}/test_trigger/{trigger_id}` per step
   1's host-derivation note (plain text if no web host could be derived).
   The Note column always leads with a base clause naming what version
   the trigger is currently on: "Passing on `X`" or "Failing on `X`",
   using the bare docker tag (strip the registry/image path, e.g.
   `registry.example.com/company/variant_calling:1.2.0-260816-b8833cb` →
   `1.2.0-260816-b8833cb`) so the cell stays narrow — but once stripped,
   never truncate or abbreviate the tag itself, same rule as step 6's
   root-cause table. Link `X` (and any other tag mentioned in the same
   cell) to that specific run's `{web_host}/test_chain_run/{tcr_id}` when
   a web host is available. Layer whatever pattern step 2 found on top of
   that base clause, don't replace it:
   - **recovered** — append ", previously failing up to {date of the last
     failing run} (`{that run's version}`)", e.g. "Passing on `X`,
     previously failing up to 2026-08-09 (`Y`)", with `Y` linked to its
     own TCR the same way as `X`.
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
     - **check-config issue** — the run's content and the baseline are both
       fine; the *check itself* is misconfigured (e.g. a percent-diff
       assertion set to zero tolerance, so ordinary floating-point noise
       trips FAIL every run regardless of version). Neither a regression
       nor a stale baseline — it's a threshold/assertion fix owned by
       whoever maintains the check definition, not the baseline owner.
   - **A check whose diff detail is only an aggregate match percentage
     (e.g. `"check_result": "14.286%"` with empty `diff_indexes`/`diffs`
     in `diff_details_raw`) has no field-level breakdown available from
     the API** — common for tabular file-compare checks. `inspect_execution_outputs`
     can't fill this gap either: by design it returns only column
     headers/types, never actual data values. Don't silently drop or
     skip such a check because "there's nothing to show" — report the
     aggregate diff you did see and say explicitly that the specific
     differing field/metric isn't retrievable through the connected
     tools, so a human would need to open the actual output file (e.g.
     via the Miqa web UI) to identify it.
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
   | [gdc-str-release](https://{web_host}/test_trigger/fb8e25c4) | 🔴 Real regression | CLI flag renamed `--bam-input`→`--bam`, crashing since [TCR 60301](https://{web_host}/test_chain_run/60301) (`1.2.0-DRAFT-260811-6e5c587`) |
   | [rc-release](https://{web_host}/test_trigger/46f9b657) | 🟡 Needs baseline update | `@release_series` baseline frozen since [TCR 59905](https://{web_host}/test_chain_run/59905), "no comparison version found" |
   | [ssvc-tn-release](https://{web_host}/test_trigger/54157ec2) | 🟢 Healthy, still running | [TCR 60304](https://{web_host}/test_chain_run/60304) within normal ~10.5h runtime, not stalled |
   | [demux-release](https://{web_host}/test_trigger/525aae1b) | 🟢 Recovered | `@release_series` baseline pointer broken ([TCR 60238](https://{web_host}/test_chain_run/60238)–[60272](https://{web_host}/test_chain_run/60272)); admin repointed baseline + force-rebaselined history on [TCR 60278](https://{web_host}/test_chain_run/60278); current runs pass organically |

   Use 🔴 for a real product regression, 🟡 for either "needs a baseline
   update" (stale/frozen baseline pointer, comparison version swapped to
   something incompatible, or baseline files deleted — the baseline itself
   is the problem right now) or "check-config issue" (the check's own
   assertion/threshold is misconfigured, e.g. a zero-tolerance percent-diff
   catching float noise) — name which of the two it is explicitly in the
   cell text rather than defaulting both to "needs baseline update"; they
   have different owners (test-config/baseline owner vs. whoever maintains
   the check definition). 🟢 for healthy/passing/still-running-normally
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
   tag down to just the TCR number. Link each "TCR NNNNN" citation and the
   Trigger name to `{web_host}/test_chain_run/{tcr_id}` and
   `{web_host}/test_trigger/{trigger_id}` respectively when step 1 derived
   a web host; otherwise leave them as plain text — don't fabricate a
   link. Aim for roughly one sentence
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
   version too, e.g. "Want this as a polished, shareable report? I can
   publish it." — don't guess or assume interest, just surface the option
   so the user doesn't have to already know an Artifact version exists in
   order to ask for it. Don't publish anything unless they say yes; if
   they don't respond to the offer or move on to something else, drop it,
   don't re-offer on a later sweep in the same conversation.

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
     / needs-baseline-update / check-config — it belongs to, don't fold it
     into the main narrative's diagnosis), and separately, any WARN-status
     finding uncovered while root-causing (see step 6's "WARN is not a
     second root cause" rule) — always flagged, never given the main case's
     `<h3>`/`.boundary`/`.proof` treatment, always read as a footnote. A
     plain mono footer with host + sweep date closes the page.
   - **Title & favicon** — title names the sweep as a plain noun phrase,
     no dash-appended explainer (e.g. "August 25 Trigger Sweep", not
     "Trigger Health — Aug 25"); favicon is always 🧬.
   - **Design history**: an earlier version of this template used a
     different card/chip treatment and (wrongly) filed a check-config issue
     under a "needs baseline update" chip. The user explicitly preferred
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
   allowance for more, not less. Working links
   to `{web_host}/test_trigger/{trigger_id}` and
   `{web_host}/test_chain_run/{tcr_id}` wherever step 1 derived a web host
   (same linking rule as the terminal tables — plain text if no web host
   could be derived, never a fabricated link). When re-running this skill
   as a follow-up ask, publish a new artifact rather than trying to update
   a prior one from a different conversation, unless the user names an
   existing artifact URL to redeploy.

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
