---
name: cli-fix-rollout
description: Use whenever a Miqa Component's actual CLI invocation/command needs to change — a renamed or newly-required flag/subcommand, a stale argument, etc. — not a baseline or check-config issue. Applies equally whether the fix was identified by a prior root-cause investigation (active-triggers or otherwise) in this conversation, or the user just asks directly to fix/update a component's command with no investigation at all — the skill establishes the failing streak itself in the latter case. Rolls the fix out starting at the FIRST failing Test Chain Run in the streak (every ComponentVersion touched by that streak, not just the latest), dry-running the command edit and getting explicit permission before applying, then dry-running and applying execution retries. Trigger phrases include "fix the CLI/command", "update the component version's command", "the docker command is wrong/needs a new flag", "roll this fix out from the first failure", "retry these runs after the fix".
metadata:
  version: 1.2.4
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

Derive the Miqa web UI host once, up front, the same way the
`active-triggers` skill does: read the `MIQA_SERVER_URL` env var backing the
connected Miqa MCP server (e.g. a one-off `echo $MIQA_SERVER_URL`). If it
matches `api.<env>.miqa.io` (starts with `api.`, ends with `.miqa.io`), the
web host is `<env>.miqa.io` — strip the leading `api.`. If it doesn't match
that shape (a raw gateway/Zuplo-style host with no `.miqa.io` suffix), don't
guess a web host at all, and skip the link in step 4's web-UI fallback
(describe the fallback without a URL instead).

**Only enter this flow when a command/CLI-level fix is the remedy** — a
renamed/missing flag or subcommand, a stale argument. That determination
can come from a prior root-cause in this conversation (e.g. `active-triggers`
concluding "real product regression" with a quoted CLI error), or the user
can simply ask directly ("the component's command needs a subcommand now",
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

2. **Start from just the first failing ComponentVersion — don't collect the
   whole set up front.** Call `list_component_versions_for_test_chain_run(run_id)`
   for the boundary TCR the user confirmed in step 1 only, and use the exact
   `(component_id, component_version_id)` pair from that result — never
   match by display name (the tool's own docs warn against this; display
   names collide across versions). Build and dry-run the fix (steps 3-5)
   against this one version first, so the reconstruction is validated before
   spending any calls on the rest of the range.

   Once the user has confirmed that first version's diff, walk forward
   through the rest of the confirmed range one TCR at a time: call
   `list_component_versions_for_test_chain_run` for each subsequent TCR
   (sampling is fine across a long range, but never skip a TCR without
   checking whether it maps to a `component_version_id` you've already
   handled), then dry-run and apply the same *kind* of edit to each new
   `(component_id, component_version_id)` pair — per step 5's dry-run and
   step 7's apply — before moving to the next. If different runs in the
   streak resolve to the *same* component but different
   `component_version_id`s, every one of those IDs needs the fix
   independently — Miqa does not retroactively propagate an edit to older
   version records.

3. **Get the exact current command per version, don't reuse one string
   across all of them.** Call `get_test_trigger_template_json(trigger_id)`
   to see the current/latest version's exact `steps[].command` — this is
   your reference for what the *fixed* shape should look like structurally
   (which flag/subcommand to add, exactly where). For older versions in
   the set, don't assume they had byte-identical commands to latest before
   the fix — pull each one's current command from that version's own
   dry-run response (`update_component_version` with `apply=false` returns
   `diff.old`, which is the live value) and apply the same *kind* of edit
   (e.g. "insert the new required piece into the same position in the
   command") relative to that version's own text, not a hardcoded
   find/replace string that assumes every version matches latest
   verbatim.

4. **When the exact fix isn't fully knowable from the trigger error alone,
   construct your best effort and rank your confidence per change — don't
   stop at "I can't be sure."** A crash log's own `--help`/usage dump (often
   printed automatically when a required flag is missing), adjacent flag
   descriptions, and the current command's structure are usually enough to
   get most of the way there even when no one has confirmed the full fix.
   - Walk the current command flag-by-flag and classify each proposed
     change into three tiers internally — this classification drives what
     gets a placeholder vs. what gets asserted as a real value, so do it
     even though the full breakdown isn't always shown (see the next
     bullet):
     - **High confidence** — forced by the error message itself, or an
       exact-named match against authoritative help/docs output.
     - **Medium confidence** — a plausible rename/rewrite with matching
       semantics, type, and value range, but not proven identical.
     - **Speculative** — no clear replacement exists in the evidence at
       all; you're inferring intent (e.g. guessing that mechanism X was
       retired in favor of mechanism Y). Flag these as needing real
       verification (the tool's own changelog/docs, or a person who knows
       the CLI) before anyone trusts them.
   - **Default to a condensed presentation, not the full tiered
     table.** Skip printing the three-tier breakdown as a labeled
     High/Medium/Speculative list by default — it reads as too much text
     for what should be scannable at a glance. Instead, in one or two
     short lines of prose, name the load-bearing renamed/added flags from
     the *actual* command being fixed (using their real names from that
     pipeline, not a placeholder) and say what forced each one (e.g. "the
     two required input flags were renamed, forced by the error message").
     Follow that with one compact bullet listing the remaining
     non-placeholder translations — the Medium-confidence renames/rewrites
     that aren't forced by the error but also aren't placeholders. Hedge
     this bullet explicitly rather than asserting it as fact — these are
     inferred, not confirmed — with an opener like "From the log message,
     I think I can translate the following directly: X → Y (same
     range/semantics); A → D, B → E, C → F under a shared output setting."
     List each pairing as its own individual mapping (A → D, B → E, C → F)
     rather than grouping the old and new names into two slash-separated
     clusters (A/B/C → D/E/F) — the grouped form forces the reader to
     count positions to figure out which old flag maps to which new one,
     while individual pairings are unambiguous at a glance. Keep this
     bullet to renames/rewrites only — leave out flags that stayed
     unchanged (the diff already shows those plainly, so restating them
     here is redundant). If an unchanged flag is worth calling out at all
     (e.g. because its meaning could plausibly have shifted along with
     everything else and you want to reassure the user it didn't), put
     that in its own separate sentence rather than tacking it onto the end
     of the mapping list with a semicolon — mixing "renamed to" pairs and
     "stayed the same" facts in one run-on list blurs two different kinds
     of information together. Don't phrase
     it as "also translated directly" or similar flat assertions; the
     hedge is what tells the user this bullet is still a judgment call,
     distinct from the forced renames above it. This gives the user
     visibility into what was asserted as equivalent without a full table.
     Close the bullet with a short invitation to correct it (e.g. "let me
     know if any of those look wrong") — a hedge that never invites
     correction reads as decorative rather than a real signal that the
     mapping could be off. Keep this invitation distinct from, and
     separate in tone from, the concrete placeholder asks later in the
     message: those are required answers needed to apply the fix at all,
     this is an optional "flag it if I got something wrong" — don't let
     the two blur into one open-ended "let me know what you think"
     that reads as a menu of next steps. Then let the diff itself
     carry the rest of the detail — don't re-describe every unchanged flag
     in prose when the diff already shows it. This document's own guidance
     text should stick to generic, structural phrasing when describing the
     technique (as here) rather than naming a specific pipeline's flags as
     a worked example — that terminology belongs only in an actual
     session's fix, not in this shared skill file. Only expand into the
     full tiered breakdown if the user asks for the reasoning behind a
     specific change, pushes back on a guess, or the fix has enough
     speculative/placeholder flags that the condensed form would leave the
     risk illegible.
   - **The prose never replaces showing the actual result.** Always show
     the full reconstructed command as one complete before/after string
     (not just the individual changed flags quoted in isolation), and the
     full updated `inputs_single`/`resource_files` list if any entries
     were added or changed (not just the new entry by itself) — the same
     shape `update_component_version`'s own dry-run diff would show. The
     user needs to see exactly what the whole resulting command and file
     list would look like before confirming anything, not reconstruct it
     themselves from a bullet list of deltas. Render `inputs_single`/
     `resource_files` as a real bullet list (`dest ← source`, one per
     line), or as pretty-printed multi-line JSON with one entry per line —
     either is fine. What's never acceptable is dumping the array
     jammed onto a single line: that's what actually makes it hard to
     scan, not the JSON syntax itself.
   - **Show the full command as a git-style diff, not inline markup.**
     Present the before/after as a ` ```diff ` fenced block: a `-` line
     with the complete old command, a `+` line with the complete new
     command. This terminal renders `diff` fences with red/green
     highlighting, so the whole changed line is legible at a glance with
     no per-flag markup needed — including any placeholder tokens sitting
     in the `+` line, which read as changed by virtue of being on the `+`
     line itself. Don't wrap the command in a single fenced code block and
     then mark individual flags with nested single backticks — backticks
     nested inside a triple-backtick fence render as literal backtick
     characters, not separate code spans, so it comes out as backtick
     soup instead of a highlighted diff. Don't use bold (`**...**`) either —
     in this terminal it renders as literal asterisks around the text
     rather than actual bold, which reads worse than no marking at all.
     Do this in every place the command is shown (the initial
     reconstruction, each dry-run diff's old/new pair) — not just once up
     front.
   - If a speculative change would also alter a downstream artifact's shape
     (e.g. an output file's format or extension), say so explicitly — that
     usually means a follow-up Test Block/check edit is needed too, not
     just the Component command. Phrase the impact as "may break" rather
     than "will break": the change is still speculative at this point (the
     user hasn't confirmed it, and a web-UI edit could land on a different
     shape entirely), so hedge accordingly rather than asserting a
     downstream failure as settled fact. Don't leave this as a passing mention:
     track it through to step 9 and close the rollout by asking the user
     directly whether they want that check updated too (naming the
     specific check by name) — this skill doesn't edit Test
     Block/check config itself, so the honest close is an explicit offer
     to hand that off, not silence once the Component fix is applied. State
     that offer to help the moment you flag the downstream impact here in
     step 4, not only when step 9 actually comes around — the user should
     never read a flagged downstream break as a dangling open question with
     no owner; say plainly that once the Component fix and the open
     placeholders/questions above are resolved, you'll help update that
     check too (real fix or the interim fail→warn downgrade — see step 9).
   - **If the fix requires a genuinely new input** — a file or resource the
     ComponentVersion doesn't currently mount at all, not just a renamed
     flag — don't invent a real path. Instead, drop in an obvious,
     clearly-marked placeholder (e.g. `<PATH_TO_NEW_INPUT_FILE>`) so the
     rest of the fix can still be built and shown in full. Keep the
     placeholder name generic and structural (what kind of thing is
     missing), never named after the specific flag/domain concept from
     whatever pipeline you're currently fixing — this file is shared
     across every component this skill is ever run against, so no
     customer- or pipeline-specific terminology (tool names, flag names,
     file formats, domain vocabulary) belongs in it, examples included.
   - **If a required value is unknowable from context** (a parameter that
     depends on domain judgement, not on the CLI's own shape), do the
     same: drop in an obvious, generically-named placeholder (e.g.
     `<REQUIRED_FLAG_VALUE>`) rather than reusing an unrelated existing
     value just because it happens to share a similar valid range.
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
   - **The consolidated ask must request the actual answer, not a menu of
     next steps.** Don't close with an open-ended "want me to dry-run this,
     or hold off until you've confirmed the values?" — that hands the
     concrete asks back to the user as homework instead of just asking for
     them. Name each placeholder and ask for its real value directly, in
     the same message that shows the diff: for a `<PATH_TO_NEW_INPUT_FILE>`
     placeholder specifically, ask for the actual cloud/object-storage path
     (e.g. an S3/GCS URI) the way the rest of that ComponentVersion's
     `inputs_single` entries already reference their sources — that's the
     concrete thing needed to make the fix real, not a decision about
     whether to proceed. It's fine to *also* run the placeholder dry-run
     unprompted in the same turn (per the previous bullet) — that's a
     preview, not a substitute for asking for the value.
   - **Whenever any flag lands in the Speculative tier, or any placeholder
     exists at all, surface the web-UI fallback alongside the direct
     value-asks — every time, not just when several are stacked together.**
     This reuses the tiering work from earlier in this step, so it's not a
     new judgment call: any Speculative-tier flag or placeholder in the
     reconstructed command is itself the trigger. Point the user to that
     ComponentVersion's edit page in the Miqa web UI as an alternative to
     answering the placeholder asks in chat — they can make the edit
     themselves there with full knowledge of the correct command. When a
     web host was derived up front, give the actual link:
     `{web_host}/edit_component_version/{component_version_id}` (plain
     text is fine if no web host could be derived — never fabricate one) —
     and ask them to confirm once they've saved it. Once confirmed, pull that
     version's live command (a dry-run's `diff.old`, or
     `get_test_trigger_template_json`) and propagate the same edit to every
     other ComponentVersion in the confirmed streak (step 2's set) rather
     than leaving the rest still broken — route those remaining versions
     through the normal dry-run-then-confirm-then-apply flow (steps 5-7)
     like any other version, this isn't a shortcut around it. A fix with
     every flag at High or Medium confidence and no placeholders at all
     doesn't need this offer — don't surface it as noise on an
     already-solid reconstruction.

5. **Dry-run every version's fix before applying anything.** For each
   `(component_id, version_id)` in the set, call `update_component_version`
   with `apply=false` and the proposed new command (placeholders and all,
   per step 4 — a placeholder that fails the tool's own validation is fine
   to attempt anyway; report the rejection plainly and fall back to a
   hand-written diff for that version). Collect all the diffs — do not
   apply the first one before you've previewed the rest.
   - **Always show the complete diff returned by the dry-run — never
     summarize it, abbreviate it, or refer back to an earlier message
     ("as shown above") instead of reprinting it.** Render it the same way
     as step 4: a ` ```diff ` fenced block with the full old command on a
     `-` line and the full new command on a `+` line (not just the changed
     flags in isolation), and, whenever `inputs_single`/`resource_files`
     changed, the complete old and new lists rendered as bullets
     (`dest ← source`) or pretty-printed multi-line JSON — never jammed
     onto one line. When two or more versions in the set come back with
     byte-identical old commands (confirm this from each dry-run's own
     `diff.old`, don't assume it), show that one diff once and name every
     version it applies to instead of reprinting the same block per
     version — the user is confirming one coherent rollout, and a duplicate diff is
     exactly the kind of extra text that buries the parts that actually
     differ. Only repeat the full diff per version when the versions'
     underlying commands actually differ from each other.
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
