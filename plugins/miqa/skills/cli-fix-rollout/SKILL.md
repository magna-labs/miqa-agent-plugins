---
name: cli-fix-rollout
description: Use whenever a Miqa Component's actual CLI invocation/command needs to change — a renamed or newly-required flag/subcommand, a stale argument, etc. — not a baseline or check-config issue. Applies equally whether the fix was identified by a prior root-cause investigation (active-triggers or otherwise) in this conversation, or the user just asks directly to fix/update a component's command with no investigation at all — the skill establishes the failing streak itself in the latter case. Rolls the fix out starting at the FIRST failing Test Chain Run in the streak (every ComponentVersion touched by that streak, not just the latest), dry-running the command edit and getting explicit permission before applying, then dry-running and applying execution retries. Trigger phrases include "fix the CLI/command", "update the component version's command", "the docker command is wrong/needs a new flag", "roll this fix out from the first failure", "retry these runs after the fix".
metadata:
  version: 1.2.0
---

# Miqa CLI Fix Rollout

A command-level bug (missing/renamed flag, newly-required subcommand, bad
argument) doesn't live on one ComponentVersion — Miqa mints a new
ComponentVersion record per build tag, so a streak of N failing Test Chain
Runs on N different docker tags usually means N different broken command
records, not one. Patching only the latest one (the natural first instinct)
silently leaves every earlier failing run's ComponentVersion still broken —
a retry of an older failing TCR would still hit the old command. This skill
exists to make "fix starting at the first failure" the default, not an
afterthought.

This skill calls tools named `list_component_versions_for_test_chain_run`,
`get_test_trigger_template_json`, `update_component_version`, and
`retry_test_chain_run_executions` on whichever Miqa MCP server is connected
(tool names follow the pattern `mcp__<server-name>__<tool>`). Most setups
have exactly one Miqa MCP server connected — just use it.

**Only enter this flow when a command/CLI-level fix is the remedy** — a
renamed/missing flag or subcommand, a stale argument. That determination
can come from a prior root-cause in this conversation (e.g. `active-triggers`
concluding "real product regression" with a quoted CLI error), or the user
can simply ask directly ("the msi_caller command needs a subcommand now",
"update this component's docker command") with no investigation having
happened at all — both are equally valid entry points, see step 1. Never
trigger this off a routine sweep on your own initiative; it mutates a
shared pipeline component, unlike the read-only triage skills.

## Procedure

1. **Establish the failing streak and its boundary — running the
   investigation yourself if none already happened.** You need the exact
   first failing TCR, not just "currently failing."
   - **If this follows a root-cause investigation already in the
     conversation** (e.g. `active-triggers`), reuse the boundary run it
     already found rather than redoing the work.
   - **If the user is asking directly, with no prior investigation** —
     resolve their trigger/component/TCR reference first (via
     `list_test_triggers`, `list_test_chain_runs_for_trigger`, or
     `find_test_chain_runs_by_chain_name` — never guess an id from a bare
     name), then call `list_test_chain_runs_for_trigger(trigger_id, limit=30)`
     yourself and walk newest→oldest to find the first run (oldest) that
     shows the same failure signature as the current one. Confirm via
     `get_test_chain_run_environment` on both ends that the crash/error
     message actually matches (a long failing streak can silently change
     *why* it's failing partway through; don't assume uniformity). This is
     a first-class path, not a fallback — treat it with the same rigor as
     reusing an existing investigation.
   - **If the user wants a command change with no associated failure at
     all** (e.g. a proactive flag addition, nothing is currently broken),
     there is no streak to walk — confirm with the user which single
     version(s) they mean to target (typically just the latest), skip the
     streak/boundary logic, and proceed to step 3 for that version alone.
   - Never guess the boundary from a version name or docker tag pattern
     alone, in any of these cases.

   **Going all the way back to the true first failure is not automatic —
   confirm scope with the user before locking it in.** A streak can span
   weeks or dozens of builds; rolling a fix out across all of them may be
   far more than the user actually wants in one pass. Once you've found the
   candidate first-failing TCR, tell the user how far back it sits (date,
   TCR id, and roughly how many failing runs/ComponentVersions lie between
   it and the latest) and ask whether to fix starting there, or use a
   narrower boundary instead — a specific TCR/date they name, or just "the
   last N failing versions." Only proceed to step 2 with the range they
   confirm. This question is separate from, and comes before, step 6's
   apply-scope question (going-forward vs. one-off) — this one decides
   *which versions* are in scope at all, that one decides *how* the
   confirmed versions get patched.

2. **Collect every ComponentVersion touched across the confirmed range —
   not just the latest.** Call `list_component_versions_for_test_chain_run(run_id)`
   for the boundary TCR the user confirmed in step 1 AND the latest failing
   TCR at minimum; if the range spans more than two builds, sample the ones
   in between too
   (docker tags/versions typically change every run in an active pipeline).
   Build the set of unique `(component_id, component_version_id)` pairs
   from these results — use those exact IDs, never match by display name
   (the tool's own docs warn against this; display names collide across
   versions). If different runs in the streak resolve to the *same*
   component but different `component_version_id`s, every one of those IDs
   needs the fix independently — Miqa does not retroactively propagate an
   edit to older version records.

3. **Get the exact current command per version, don't reuse one string
   across all of them.** Call `get_test_trigger_template_json(trigger_id)`
   to see the current/latest version's exact `steps[].command` — this is
   your reference for what the *fixed* shape should look like structurally
   (which flag/subcommand to add, exactly where). For older versions in
   the set, don't assume they had byte-identical commands to latest before
   the fix — pull each one's current command from that version's own
   dry-run response (`update_component_version` with `apply=false` returns
   `diff.old`, which is the live value) and apply the same *kind* of edit
   (e.g. "insert `tumor-normal` right after the binary path") relative to
   that version's own text, not a hardcoded find/replace string that
   assumes every version matches latest verbatim.

4. **When the exact fix isn't fully knowable from the trigger error alone,
   construct your best effort and rank your confidence per change — don't
   stop at "I can't be sure."** A crash log's own `--help`/usage dump (often
   printed automatically when a required flag is missing), adjacent flag
   descriptions, and the current command's structure are usually enough to
   get most of the way there even when no one has confirmed the full fix.
   - Walk the current command flag-by-flag and classify each proposed
     change into three tiers, and present all three together rather than
     quietly folding guesses in as if confirmed:
     - **High confidence** — forced by the error message itself, or an
       exact-named match against authoritative help/docs output.
     - **Medium confidence** — a plausible rename/rewrite with matching
       semantics, type, and value range, but not proven identical.
     - **Speculative** — no clear replacement exists in the evidence at
       all; you're inferring intent (e.g. guessing that mechanism X was
       retired in favor of mechanism Y). Flag these as needing real
       verification (the tool's own changelog/docs, or a person who knows
       the CLI) before anyone trusts them.
   - **The tiered flag-by-flag breakdown explains the reasoning; it doesn't
     replace showing the actual result.** Alongside it, always show the
     full reconstructed command as one complete before/after string (not
     just the individual changed flags quoted in isolation), and the full
     updated `inputs_single`/`resource_files` array in full if any entries
     were added or changed (not just the new entry by itself) — the same
     shape `update_component_version`'s own dry-run diff would show. The
     user needs to see exactly what the whole resulting command and file
     list would look like before confirming anything, not reconstruct it
     themselves from a bullet list of deltas.
   - If a speculative change would also alter a downstream artifact's shape
     (e.g. an output file's format or extension), say so explicitly — that
     usually means a follow-up Test Block/check edit is needed too, not
     just the Component command. Don't leave this as a passing mention:
     track it through to step 9 and close the rollout by asking the user
     directly whether they want that check updated too (naming the
     specific check by name) — this skill doesn't edit Test
     Block/check config itself, so the honest close is an explicit offer
     to hand that off, not silence once the Component fix is applied.
   - **If the fix requires a genuinely new input** — a file or resource the
     ComponentVersion doesn't currently mount at all, not just a renamed
     flag — don't invent a real path. Instead, drop in an obvious,
     clearly-marked placeholder (e.g. `<PATH_TO_MICROSATELLITE_SITES_TSV>`)
     so the rest of the fix can still be built and shown in full.
   - **If a required value is unknowable from context** (a threshold or
     parameter that depends on domain judgement, not on the CLI's own
     shape), do the same: drop in an obvious placeholder (e.g.
     `<PER_SITE_THRESHOLD_VALUE>`) rather than reusing an unrelated
     existing value just because it happens to share a similar valid
     range.
   - **Don't stop at "I can't be sure" or pause before showing anything —
     build the complete fix with placeholders standing in for every
     unresolved piece, then ask the user to fill just those placeholders
     in.** Finish the flag-by-flag pass first, then present the *whole*
     reconstructed command and file list (per step 4's next bullet) with
     the placeholders sitting in their real position, and close with a
     single consolidated ask framed as "here's what I'd change — I just
     need you to fill in `<PLACEHOLDER_1>` and `<PLACEHOLDER_2>`" (naming
     each placeholder and, in one clause, what it's for) rather than a
     generic list of open questions asked before any diff is shown. Don't
     trickle the asks out one at a time either. Where it's feasible for
     the tool to accept a placeholder without erroring (see step 5), still
     run the dry-run with placeholders in place so the user sees the
     server-validated diff, not just a hand-typed reconstruction — clearly
     label that diff as containing placeholders that must be resolved
     before it can be applied.
   - **If, even after this, the fix stays too uncertain to build with
     confidence** (several speculative flags stacked together, an unclear
     file requirement, or the user doesn't have the domain knowledge to
     confirm the details on the spot) — offer the fallback: point the user
     to that ComponentVersion's edit page in the Miqa web UI so they can
     make the edit themselves with full knowledge of the correct command,
     and ask them to confirm once they've saved it. Once confirmed, pull
     that version's live command (a dry-run's `diff.old`, or
     `get_test_trigger_template_json`) and propagate the same edit to every
     other ComponentVersion in the confirmed streak (step 2's set) rather
     than leaving the rest still broken — route those remaining versions
     through the normal dry-run-then-confirm-then-apply flow (steps 5-7)
     like any other version, this isn't a shortcut around it.

5. **Dry-run every version's fix before applying anything.** For each
   `(component_id, version_id)` in the set, call `update_component_version`
   with `apply=false` and the proposed new command (placeholders and all,
   per step 4 — a placeholder that fails the tool's own validation is fine
   to attempt anyway; report the rejection plainly and fall back to a
   hand-written diff for that version). Collect all the diffs — do not
   apply the first one before you've previewed the rest.
   - **Always show the complete diff returned by the dry-run, every time,
     for every version — never summarize it, abbreviate it, or refer back
     to an earlier message ("as shown above") instead of reprinting it.**
     That means the full old command string and the full new command
     string (not just the changed flags in isolation), and, whenever
     `inputs_single`/`resource_files` changed, the complete old array and
     complete new array. Present the complete before/after set for every
     affected version together, so the user is confirming one coherent
     rollout against real diffs they can read in full, not a series of
     one-off edits or a paraphrase they have to trust.
   - If a diff still contains a placeholder from step 4, say so right next
     to that diff (e.g. "contains a placeholder — needs your answer before
     this can be applied") so it's never mistaken for an apply-ready diff.
   - **Note the classifier may throttle several dry-run calls fired back
     to back** — if a preview call is denied by the permission classifier,
     don't retry it silently or work around it; tell the user plainly
     which preview didn't go through and ask whether to retry it before
     continuing.

6. **Get one explicit go-ahead before applying anything, and resolve the
   one-off/going-forward question up front.** `update_component_version`'s
   own contract: if the version being fixed has `is_latest: false`, a
   going-forward fix also requires updating the latest version in the same
   batch — surface that requirement explicitly rather than letting the
   user discover it after applying the older one alone. Ask the user,
   for the set as a whole: apply as a going-forward fix (recommended when
   the command bug is a genuine regression that should not recur in future
   versions), or one-off per version (each fixed version stops being an
   inheritance base — appropriate only if a fresh ComponentVersion with the
   corrected command is expected to be cut separately). Do not apply
   before this is answered, and do not assume "going-forward" silently.

7. **Apply only the versions the user confirmed, one at a time, and surface
   every `resource_url`.** Call `update_component_version` with
   `apply=true` for each confirmed `(component_id, version_id)`. Per the
   tool's own contract, whenever the result contains `resource_url`, show
   it to the user — don't summarize it away. If any apply call errors
   (validation rejection, unknown variable, etc.), stop and report that
   specific error verbatim rather than proceeding to the next version
   silently.

8. **Retry the affected executions — dry-run, then apply, as its own
   separate confirmation.** For each TCR in the streak that should be
   re-run (typically every failing TCR from the first failure through the
   latest), call `retry_test_chain_run_executions` with `apply=false`
   first and present the count/execution-ID set it returns. This is a
   distinct action from step 7's command fix — get a second explicit
   confirmation before calling it again with `apply=true`, even if the
   user already approved the command fix. Don't default to `all=True`
   (which would also re-run already-passing executions) unless the user
   asks for that.

9. **Report what actually changed.** Close with a short summary: which
   ComponentVersions were patched (id + name + old→new command), whether
   it was applied going-forward or one-off, and which TCRs had retries
   kicked off (with their `resource_url`s). Retries run asynchronously —
   don't claim success for the underlying bug until a retried run actually
   completes; offer to check back on the retried TCRs rather than assuming
   they passed. If step 4 flagged a downstream check that a speculative
   change would break, this is where that gets closed out — ask explicitly
   whether the user wants that check updated too, naming it by name; don't
   let it quietly drop off once the Component fix lands. Offer both a real
   fix (updating the check's file pattern/logic to match the new output
   shape) and a lighter interim option (temporarily downgrading that
   check's `failtype` from fail to warn, so the still-uncertain downstream
   mismatch stops masking other real failures on the same run without
   pretending it's resolved) — let the user pick, don't default to either.

## Notes

- This skill mutates shared pipeline configuration and starts real
  execution retries — every apply-type call (command fix, retries) needs
  its own explicit user confirmation. Never chain "user approved the fix"
  into "so retries are pre-approved too."
- If the user only names a TCR or docker tag rather than a trigger, resolve
  it to a trigger via `list_test_chain_runs_for_trigger` /
  `find_test_chain_runs_by_chain_name` first — same rule as the other Miqa
  skills, never guess the trigger from a bare ID.
- If step 2 finds that every run across the whole streak actually shares
  one single `component_version_id` (a slower-moving component that isn't
  rebuilt every run), the "starting at the first failure" set collapses to
  just that one version — that's fine, don't force multiple edits where
  only one exists.
