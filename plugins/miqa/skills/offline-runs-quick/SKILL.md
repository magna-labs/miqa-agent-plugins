---
name: offline-runs-quick
description: Use when the user wants the fast, low-ceremony version of miqa:offline-runs-to-test, e.g. "quick offline test", "easy mode offline runs", "just make a test from these output folders", "offline runs from this spreadsheet/csv/json/yaml", "compare these two versions of the same samples". Takes samples with their output locations (one version, or a baseline and a test version) as a paste, a csv/excel/json/yaml file, or parent folders to discover samples in. Asks only for a version name and a test name, lists its assumptions, asks for ONE confirmation, then creates everything end to end (missing datasets, offline version(s), executions, dataset group, test block, chain and chain run). The checks are either one basic "outputs have at least 1 file" check, checks it suggests from the files, or checks translated from the user's requirements; anything beyond the basic check is run on real pairs and controls before it is saved. It narrates as it goes, announces completion and copies the test chain link right away, then rechecks the results and publishes a private report page. For existing blocks or hand-chosen metadata use miqa:offline-runs-to-test instead.
metadata:
  summary: Fast offline-runs path: one confirmation, baseline and test versions, checks proven before saving, a report page.
  version: 0.1.0
---

# Offline Runs, Quick

The short path of `miqa:offline-runs-to-test`. Fewer questions, one permission ask, a report at the end. Tool names differ
between deployments (some carry an `api_` prefix); use whatever the connected Miqa server offers.

## 0. Stay live

The user should never wonder whether anything is happening. Write one short plain line **before** each step, and again
whenever a step may take more than a few seconds. Keep each line to what is happening and why, not a recap.

- Before a read-only phase: "Looking up the pipeline and checking which samples already exist."
- Inside a multi-item step, give a counter: "Creating executions, 5 of 10." Print a line every few items, not every item.
- When waiting on Miqa, say so and say what happens next: "The results summary is still generating. Retrying, 2 of 4."
- When a step is slow by nature (results summaries, discovery of many folders), say roughly how long it should take.
- After a batch of tool calls, one line of what came back before the next batch. No long silences.
- Do not narrate trivia, and do not repeat what the previous line already said.

## 1. Gather inputs

**Samples and output locations** can arrive four ways. If none was given, ask for one in a plain message. Never ask for
anything the input already answers.

1. **Pasted lines.** `name, bucket/folder`. With two versions, add the version: `name, version, bucket/folder`, or give
   `name, baseline bucket/folder, test bucket/folder`. Strip a leading `s3://` or `gs://`; split bucket from folder at the
   first slash.
2. **A file** (csv / tsv / xlsx / json / yaml). See below.
3. **Parent folders.** "Baseline is `bucket/prefix_a`, test is `bucket/prefix_b`, figure out the samples." See section 2.
4. **An existing dataset group.**

Reading a file (user's own file; read it with a script, do not paste its contents into the conversation):
- csv/tsv: python `csv`. json: `json`. yaml: `yaml` if importable. xlsx: `openpyxl` if importable, first sheet.
  If a parser is missing, say which and ask for a csv export instead of installing anything.
- Find columns by header, case-insensitive, first match wins:
  - sample name: `sample`, `sample_name`, `name`, `dataset`, `datasource`
  - version: `version`, `build`, `run`. Absent means a single version.
  - location, any of: one column holding `bucket/folder`, `s3://bucket/folder` or `gs://bucket/folder`
    (`location`, `output_location`, `path`, `uri`, `url`), or separate `bucket` + `folder` (`output_folder`, `dir`)
  - optional `prefix` / `file_prefix`
  - every other column is a candidate **metadata** field. It is used only if its header matches a field in the
    pipeline's dataset schema, and only for datasets this run creates. Extra columns are ignored and listed in the plan.
- json/yaml may be a list of records or a map of sample name to location or record; treat both the same way.
- If a column choice is ambiguous, say what you picked in the plan instead of asking.

**Pipeline** (id or name): take it from the arguments, the file (a `pipeline` column) or ask once.

**Names, with AskUserQuestion** (interactive prompt, suggested options). Ask in two steps, because the second depends
on the first. If the user already gave a name, use it and skip that step.
1. Version name(s). Options: `offline-<YYYY-MM-DD>` (recommended) and the same with `-b`, `-e2e` or similar if that name
   is already taken. With two versions, ask for the baseline and test names together, with `-v1` / `-v2` style defaults.
2. Test name. Build the options from the version name the user chose: `<version> any-file-exists` (recommended),
   `<version> outputs-not-empty`, `<version> smoke`. For two versions: `<baseline> to <test>`. "Other" is always there.

The dataset group is named `<test name> group`. Do not ask for it.

## 2. Look before you write (read-only, no prompts)

Narrate this phase (section 0). Everything here is read-only.

- `get_org_context`. One org: use it. Several and none selected: ask which, in the same step as the names. Hosted servers
  cannot switch org; pass `org_id` to tools that take it, and note in the plan which org requests will run in.
- Resolve the pipeline. Match sample names against the pipeline's datasets.
- Read the offline-version options; use the default variant (or the only one). Note: a variant can show
  `is_default: false` when it is the only one.
- Read the dataset schema if any sample is missing.

**Discovering samples from parent folders** (only when the user gave parent folders):
- Use `list_output_prefix` (`pipeline_id`, `bucket`, `prefix`, `org_id`). It returns the immediate subfolders with file
  counts and says when it cut the list short; raise `max_folders` (up to 500) or narrow the prefix when it did. If the
  tool is not available on this deployment, say so and ask the user for the folders instead. Do not guess locations.
- Folder names can carry a run suffix such as `-0f66ee9c61d4e7a8` (a dash and 16 hex characters). Strip it before
  matching names.
- Match folders to sample names in this order: exact, then ignoring case and `_`/`-`, then prefix or suffix containment.
  **Always show the mapping as a table in the plan.** Never match silently.
- If several folders map to one sample (repeated runs), list the candidates with file counts and ask which to use. Do not
  pick one. Folders that matched nothing are listed too.

**Two versions with different samples.** Compute three lists: only in baseline, only in test, in both. If they differ,
say so plainly and ask (in the confirmation, section 3) whether to take just the overlap (default), also bring the rest in
without comparing them, or stop. Compare only the overlap.

## 3. One confirmation

Print the single plan as text, then ask once with AskUserQuestion. No second confirmation. Questions to ask together:

1. Create everything as planned / change something.
2. **What should the test check?** Options: *Basic check only* (recommended: "outputs have at least 1 file", add more after
   seeing real results), *Suggest some for me* (you propose checks from the real files), *I'll give requirements* (they
   paste a list and you translate it). Skip this question if the user already said.
3. Only when the sample lists differ: take the overlap / bring the rest in uncompared / stop.

The plan lists:

- what will be created, with counts: datasets (names), offline version(s), executions, group, test block, chain, chain run;
- the input source (paste, file with the column mapping, or the folder-to-sample table);
- **Assumptions**, as they apply:
  - new datasets get the metadata found in the file, otherwise **blank metadata**, and **no files**;
  - default workflow variant `<name>` is used;
  - output location splits at the first `/`; file prefix as given, otherwise none;
  - with two versions, the baseline version is created first so it is the "previous version" for the test version;
  - checks use fail type **warn** (they show as warnings and do not fail the run); say how to switch to `fail`;
  - the basic check is "Outputs should have at least 1 file": a `file_collection` check, `stat` `data.total_count > 0`,
    detail `data.total_count`; it says nothing about which files or how many;
  - the chain run picks up every sample in the group for each version;
  - which org requests run in, if it could not be selected;
- what will NOT happen: no existing dataset, group, block, chain or version is changed.

A "yes" covers every write in the plan, plus the clipboard copy and the private report page. Anything else needs a new ask.

## 4. Create (in this order, stop on the first failure and report it)

Narrate with counters (section 0).

1. Missing datasets: batch upsert by name, with file metadata where present, no files.
2. Offline version(s): baseline first, then test. Chosen names and variant.
3. One execution per sample per version, with bucket, folder and prefix.
4. Dataset group from the sample dataset ids (the overlap only, if the lists differed), associated with the pipeline.
5. **Checks.** Basic: go straight to step 6. Suggested or from requirements: **draft the checks by following the
   `miqa:assertion-translator` skill, not from memory or from the gotchas below.** Invoke it before writing any check.
   It requires: the Miqa docs lookup for each topic, the live vocabulary, its patterns reference, `inspect_execution_outputs`
   on the real executions (both of them for a baseline/test pair), a `description` on every check, a bound value
   (`_precompute` plus `detail_display_stat`) for every Boolean threshold check, and its validation command. Its most
   important structural rule: **every top-level group key must be exactly the `check_type` shared by every check inside
   that group** (comparative checks live in `paired_file_collection`, `paired_tabular_mdo_eval`,
   `file_collection_compare` and so on, never in a group with a made-up name such as `paired` or `metrics`); the schema
   validator does not catch this. Then do section 5 before step 6, because a test block needs its checks when it is
   created. The gotchas in section 5 only add what was seen on specific deployments; they do not replace the translator.
6. Test block through a chain: `create_through: "chain"`, `datasource_group_id` = the group, `test_name` = the chosen
   name. One version: `execution_id` = the first execution. Two versions: `baseline_execution_id` and
   `test_execution_id` of the first overlapping sample. Miqa creates one chain run per version; the comparison is the run
   for the test (newest) version.
7. Find the chain run(s) by chain name.

**Changing the block afterwards.** `update_test_block` is a full replace with no preview. It takes effect at once and
creates a new block version on every call, even if the content is unchanged; the earlier version stays in the history.
Existing chain runs stay on the block version they were created with, and a recheck re-evaluates them against that
version, so new checks do not appear on a run that already exists (tested: recheck of the comparison run after an update
still showed the old four checks, version unchanged). So far the new checks only show on a new chain run.

**Wanted, not yet working: change the block after creation and have it apply to the existing runs.** Updating the block
works. Applying it does not, and these are ruled out: recheck of the chain run (does not re-pin the version);
`set_test_block_run_version_overrides` (it changes which earlier block run a check compares against, not the block
version); `create_test_block` with `create_through: "chain"` (makes a new chain, it does not add a block to the existing
one). Still to try: `recheck_test_block_run` on its own, running the existing trigger or a new chain run, and checking
the Miqa web UI for a way to move a run to the current block version. Until one works, say plainly that the update
applies to new runs, and do not promise that a recheck will show the new checks.

Basic assertions (fail type `warn`):
`{"file_collection": {"report": true, "checks": [{"name": "Outputs should have at least 1 file", "check_type": "file_collection", "stat": "data.total_count > 0", "detail_display_stat": "data.total_count", "failtype": "warn"}]}}`

## 5. Prove the checks before saving them

Applies to any check beyond the basic one, and runs on checks drafted with `miqa:assertion-translator` (section 4,
step 5). A schema validator only checks syntax; it does not run the expression, and a
check can validate cleanly and still error or never fail. Run every drafted check with the ad-hoc assertion run (nothing
is persisted) on real executions first.

**Order of the runs (two versions).**
1. **Self-self first, on all assertions.** Take the first sample's baseline execution and use it as both baseline and
   test, with every drafted check plus the sentinels. This is the happy path. If anything errors or comes back incomplete
   here, fix it before going on (check the group name first). The only exception is a check built for a static baseline
   that has different files from the test, and the check already accounts for that.
2. **Same sample, baseline version against test version.** Not everything has to pass, but there should be no errors and
   nothing incomplete.
3. **A different pair of the same samples, baseline version against test version.** Same expectations. Never pair two
   different samples; Miqa refuses.

You will not know which pairs are supposed to pass or fail, so use controls with known answers instead:

- **Pair 1:** the first overlapping sample (baseline vs test, or the single execution).
- **Pair 2:** a second sample chosen **at random** from the rest. Say which one you picked.
- **Sentinel (must fail):** one always-false check for each check type used, for example `data.files.count < 0` (file
  collection), `data_baseline.files.count == -1` (paired), `data.rows.count < 0` (tabular). If a sentinel does not fail,
  that check type cannot gate. Stop and report it.
- **Identity (must pass):** run each comparative check with the same execution as both baseline and test (tested 2 Nov
  2026: the name check, the size check and a paired tabular check all passed, once the group name matched the check
  type; see the first gotcha). A comparative check that fails against itself, or comes back incomplete, is not proven.
- **Natural bad pair (should fail), when one exists:** you cannot compare two different samples (Miqa refuses with
  "Datasets do not match", even with `force_compare`), so look for a pair that visibly differs without any domain
  knowledge: compare the file counts (the run's execution stats, or the folder listing) of every baseline/test pair. A
  pair with different counts must make a "same files" check fail. If no pair differs, say the check has not been shown
  to fail on real data.

Accept a check only if: it produced no evaluation error on any run, it passed the identity control, and its sentinel
type failed. If an expression errors, read the message, fix the expression and rerun. Do not save a check that errored.
Also read the per-check result, not just the overall status: a comparative check can come back "incomplete" with no value
when the pair is not comparable.

Report per check what was shown, not that it is correct: pair 1 outcome, pair 2 outcome, the observed value (from the
detail), and flags such as "never seen failing" or "passed on a mismatched pair". A check that passed everywhere ran clean
but has not been shown to catch anything. Say so. Checks that are held back are listed with the reason, and saved only
after a new ask. If the user gave expected outcomes, use them as extra known-answer tests.

### Expression gotchas (seen on the AWS deployment on 2 Nov 2026; the public docs are wrong on several, so verify)

- `.sort()` sorts in place and returns nothing, so `list.sort() == list.sort()` **always passes**. To compare file names
  regardless of order use `data_baseline.files.map('basename').sorted_alphabetically() == data_test.files.map('basename').sorted_alphabetically()`
  (the `sorted(...)` builtin also works). Both failed on a pair with a missing file and passed on an identical pair.
- Same file sizes: `data_baseline.size_by('basename') == data_test.size_by('basename')`.
- Aggregates on a mapped column are properties, not calls: `data.rows.map('col').min`, `.max`, `.mean`, `.sum`,
  `.median`, `.unique`. The called forms (`.min()`) return no result.
- `.length` and `.is_unique` returned no result in either form on a mapped tabular column; avoid them until confirmed.
- A boolean stat hides the number. Bind the value in `_precompute` and set `detail_display_stat` to it.
- Worked when tested: `data.has_sibling_files('.bam', ['.bam.bai'])`, `data.files.with_size_less_than(1).count`,
  `data.files.with_extension([...]).count`, `data.files.map('extension').unique`, `files.frequency('extension')`.
- Paired checks use `"versions": [-1]` and compare with the previous version of the same sample.
- **The group (assertion category) name must equal the check type for comparative checks (found 2 Nov 2026, awstest,
  org Demo, pipeline 219).** Put `paired_file_collection` checks in a group called `paired_file_collection`,
  `paired_tabular_mdo_eval` checks in `paired_tabular_mdo_eval`, and `file_collection_compare` in
  `file_collection_compare`. The same checks in groups I had named `paired` or `metrics` came back "incomplete" with
  empty `detailed_results`, and the paired sentinel could not fail. A paired check placed in a `file_collection` group
  gives the message "This was not an expected check type" and its sentinel wrongly passes. Changing `data` to
  `data_test`, using block run ids, or adding `sources`/`wfv_ids` made no difference; the group name did. With the right
  group names, self-self and v1-vs-v2 runs completed, the sentinels failed, and the checks failed on pairs whose files
  differ (details in section 5 order). If a paired check is incomplete, check the group name first.
- Prototype queries (`count_files`) have returned 0 for patterns that should match. Do not use them to judge a check.

## 6. Say it is done, right away

Before any results check:
- Copy the new **test chain** link (`.../test_chain/<id>`) to the clipboard with `pbcopy` (macOS). If that fails, just
  print it.
- Print a short "done" message: what was created and every link the server returned (versions, group, block, chain, chain
  runs). Say that the results check and the report page are next. Do not wait for the user.

## 7. Recheck the results (automatic)

- Read the run environment for the test run: every sample's execution should be Done.
- Read the run results. If the summary is still generating, retry up to 3 more times with a short wait between (say
  "retrying, n of 4" each time); then continue with the result marked pending. Do not loop longer. Foreground `sleep` may
  be capped; if it is blocked, just retry the call.
- Judge results only by what the server reports. If a check errors or reports FAIL, say so plainly and offer a corrected
  new block; never edit existing ones.

## 8. Publish the report page (private, automatic)

Load `artifact-design`, then build the page from `report-template.html` in this skill's folder: copy it to the
scratchpad, replace the `{{...}}` placeholders and delete any section that does not apply, then publish with a
`report` icon. Publish even when the result is pending. Use the plain words the server returned; no invented success.

Finish with a short terminal message: the result as reported (or pending), the report link, and the next step.

## 9. Next step

If only the basic check was used: say the test exists and can be opened now, and ask whether they want to build checks
around their actual data (suggest some, or paste requirements). If they pick requirements, hand off to
`assertion-translator` (draft from what they describe, using the executions just created), and apply section 5 to what it
drafts. Create nothing until the user confirms. Never start this unprompted.

## Never

- write before the single confirmation, or beyond what the plan listed;
- invent metadata, patterns, counts, sample-to-folder matches or output locations, or match folders to samples silently;
- change or delete existing datasets, groups, blocks, chains or versions;
- save a check that errored when it was run, or call a check verified beyond what actually ran;
- report a run as passing, or executions as complete, that the server has not reported so;
- go quiet through a slow step;
- install packages to read an input file.
