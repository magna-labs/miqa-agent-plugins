---
name: offline-runs-to-test
description: Use when the user has results from runs that happened outside Miqa and wants them in Miqa, e.g. "I have outputs for these samples in a bucket", "bring these offline runs into Miqa", "set up executions for these samples", "start from these output folders and make a test", "quick offline test", "just make a test from these output folders", "compare these two versions of the same samples", "offline runs from this spreadsheet/csv/json/yaml" (via a connected Miqa MCP server). Takes samples with where each sample's outputs live, for one version or for a baseline and a test version, as a paste, a csv/excel/json/yaml file, parent folders to discover samples in, or an existing dataset group. Creates an offline version (or two) and one execution per sample, and can go on to create missing datasets, a dataset group, and a test block, chain and linked chain run. Has two modes. Quick mode asks only for version and test names, lists its assumptions, asks ONE confirmation, creates everything end to end, narrates as it goes, copies the chain link, rechecks the results and publishes a private report page; its checks are one basic "outputs have at least 1 file" check, checks suggested from the real files, or checks translated from the user's requirements, and anything beyond the basic check is run on real pairs and controls before it is saved. Step-by-step mode asks for approval at each stage and covers hand-chosen dataset metadata, executions only, and copying an existing block. Writes only after confirmation.
metadata:
  summary: From samples and output locations to executions, a group and a chain run with checks, in a quick one-confirmation mode or step by step.
  version: 0.3.0
---

# Offline Runs to Test

Start from outputs that already exist and go as far as the user wants: executions only, executions in a dataset group,
or all the way to a test block, a chain and a chain run that contains every sample's execution. Everything specific
(pipeline, field names, file patterns) comes from the user or from the server. Nothing about any particular pipeline
belongs in this file.

Tool names differ between deployments (some carry an `api_` prefix). This file names the operations in words; use
whichever tool name the connected server offers. Call `get_org_context` first where it exists.

## Pick a mode

- **Quick mode** when the user asks for the quick, easy or one-confirmation path, just wants a test around their
  outputs, gives parent folders or a spreadsheet, or wants two versions of the same samples compared. One confirmation
  covers every write.
- **Step-by-step mode** when the user wants to approve each stage, wants to choose dataset metadata by hand, wants
  executions only or an existing dataset group, or wants to copy an existing test block.

Say which mode you are using in your first line. Both modes share the narration rule, the inputs and the read-only
lookups below.

### One version or two

Either mode takes one version or a baseline and a test version.

- **Two versions.** The first is the baseline and the second is the test. Create the baseline first so it is the
  "previous version" for the test. Compare only samples present in both.
- **One version.** Create one offline version and one execution per sample, and no second version or second set of
  executions. Treat that version as both baseline and test: pass the same execution as the baseline and as the test
  (a block created with a single `execution_id` self-compares). Any check type is
  allowed, including comparative checks (`"versions": [-1]`), and comparative checks will pass by construction (a
  version compared with itself), apart from deliberate negative cases. Say in the report that comparative checks tell the
  user nothing until a second version exists.

## Stay live (both modes)

The user should never wonder whether anything is happening. Write one short plain line **before** each step, and again
whenever a step may take more than a few seconds. Keep each line to what is happening and why, not a recap.

- Before a read-only phase: "Looking up the pipeline and checking which samples already exist."
- Inside a multi-item step, give a counter: "Creating executions, 5 of 10." Print a line every few items, not every item.
- When waiting on Miqa, say so and say what happens next: "The results summary is still generating. Retrying, 2 of 4."
- When a step is slow by nature (results summaries, discovery of many folders), say roughly how long it should take.
- After a batch of tool calls, one line of what came back before the next batch. No long silences.
- Do not narrate trivia, and do not repeat what the previous line already said.

## Inputs (both modes)

**Samples and output locations** can arrive four ways. If none was given, ask for one in a plain message. Never ask for
anything the input already answers.

1. **Pasted lines.** `name, bucket/folder`. With two versions, add the version: `name, version, bucket/folder`, or give
   `name, baseline bucket/folder, test bucket/folder`. Strip a leading `s3://` or `gs://`; split bucket from folder at the
   first slash.
2. **A file** (csv / tsv / xlsx / json / yaml). See below.
3. **Parent folders.** "Baseline is `bucket/prefix_a`, test is `bucket/prefix_b`, figure out the samples." See
   "Discovering samples from parent folders".
4. **An existing dataset group.** List its datasets.

Reading a file (user's own file; read it with a script, do not paste its contents into the conversation):
- csv/tsv: python `csv`. json: `json`. yaml: `yaml` if importable. xlsx: `openpyxl` if importable, first sheet.
  If a parser is missing, say which and ask for a csv export instead of installing anything.
- Find columns by header, case-insensitive, first match wins:
  - sample name: `sample`, `sample_name`, `name`, `dataset`, `datasource`
  - version: `version`, `build`, `run`. Absent means a single version.
  - location, any of: one column holding `bucket/folder`, `s3://bucket/folder` or `gs://bucket/folder`
    (`location`, `output_location`, `path`, `uri`, `url`), or separate `bucket` + `folder` (`output_folder`, `dir`)
  - optional `prefix` / `file_prefix`
  - optional `pipeline`
  - every other column is a candidate **metadata** field. It is used only if its header matches a field in the
    pipeline's dataset schema, and only for datasets this run creates. Extra columns are ignored and listed in the plan.
- json/yaml may be a list of records or a map of sample name to location or record; treat both the same way.
- If a column choice is ambiguous, say what you picked in the plan instead of asking.

**The pipeline** (id or name): take it from the arguments, the file (a `pipeline` column) or ask once. Otherwise read it
from a dataset: the dataset detail lists its pipeline ids. The list-pipelines operation may be missing on older
backends; do not rely on it.

**Where each sample's outputs are:** bucket and folder, optionally a file prefix. One location can be shared by all.
If the user points at an existing run, read its locations from that run's environment (the run-environment operation)
and split the combined `bucket/folder` string at the first slash. Do not use the run-details operation to read it; it
can fail with an output validation error on some servers.

**How far to go:** executions only, plus a group, or through a test. If the user does not say, do executions and ask
whether they want a group and a test. (Quick mode always goes through the test.)

**Names, with AskUserQuestion** (interactive prompt, suggested options; quick mode). Ask in two steps, because the
second depends on the first. If the user already gave a name, use it and skip that step.
1. Version name(s). Options: `offline-<YYYY-MM-DD>` (recommended) and the same with `-b`, `-e2e` or similar if that name
   is already taken. With two versions, ask for the baseline and test names together, with `-v1` / `-v2` style defaults.
2. Test name. Build the options from the version name the user chose: `<version> any-file-exists` (recommended),
   `<version> outputs-not-empty`, `<version> smoke`. For two versions: `<baseline> to <test>`. "Other" is always there.

The dataset group is named `<test name> group`. Do not ask for it.

## Look before you write (both modes; read-only, no prompts)

Narrate this phase. Everything here is read-only.

- `get_org_context`. One org: use it. Several and none selected: ask which, in the same step as the names. Hosted servers
  cannot switch org; pass `org_id` to tools that take it, and note in the plan which org requests will run in.
- Resolve the pipeline. List the pipeline's datasets and match sample names against them. Report matches and unmatched
  names.
- Read the offline-version options; use the default variant (or the only one). Note: a variant can show
  `is_default: false` when it is the only one.
- Read the dataset schema if any sample is missing.

### Discovering samples from parent folders (only when the user gave parent folders)

- Use `list_output_prefix` (`pipeline_id`, `bucket`, `prefix`, `org_id`). It returns the immediate subfolders with file
  counts and says when it cut the list short; raise `max_folders` (up to 500) or narrow the prefix when it did. If the
  tool is not available on this deployment, say so and ask the user for the folders instead. Do not guess locations.
- Folder names can carry a run suffix such as `-0f66ee9c61d4e7a8` (a dash and 16 hex characters). Strip it before
  matching names.
- Match folders to sample names in this order: exact, then ignoring case and `_`/`-`, then prefix or suffix containment.
  **Always show the mapping as a table in the plan.** Never match silently.
- If several folders map to one sample (repeated runs), list the candidates with file counts and ask which to use. Do not
  pick one. Folders that matched nothing are listed too.

### Two versions with different samples

Compute three lists: only in baseline, only in test, in both. If they differ, say so plainly and ask (in the
confirmation) whether to take just the overlap (default), also bring the rest in without comparing them, or stop.
Compare only the overlap.

---

# Quick mode

## Q1. One confirmation

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

## Q2. Create (in this order, stop on the first failure and report it)

Narrate with counters.

1. Missing datasets: batch upsert by name, with file metadata where present, no files.
2. Offline version(s): baseline first, then test. Chosen names and variant.
3. One execution per sample per version, with bucket, folder and prefix.
4. Dataset group from the sample dataset ids (the overlap only, if the lists differed), associated with the pipeline.
5. **Checks.** Basic: go straight to step 6. Suggested or from requirements: **draft the checks by following the
   `miqa:assertion-translator` skill, not from memory or from the expression notes in `references/proving-checks.md`.** Invoke
   it before writing any check. It requires: the Miqa docs lookup for each topic, the live vocabulary, its patterns
   reference, `inspect_execution_outputs` on the real executions (both of them for a baseline/test pair), a
   `description` on every check, a bound value (`_precompute` plus `detail_display_stat`) for every Boolean threshold
   check, and its validation command. Its most important structural rule: **every top-level group key must be exactly
   the `check_type` shared by every check inside that group** (comparative checks live in `paired_file_collection`,
   `paired_tabular_mdo_eval`, `file_collection_compare` and so on, never in a group with a made-up name such as `paired`
   or `metrics`); the schema validator does not catch this. Then read `references/proving-checks.md` and prove the
   checks before step 6, because a test block needs its checks when it is created. The expression notes there only add what
   can differ between deployments; they do not replace the translator. With one version, use the same execution as
   baseline and test (see "One version or two").
6. Test block through a chain: `create_through: "chain"`, `datasource_group_id` = the group, `test_name` = the chosen
   name. One version: `execution_id` = the first execution. Two versions: `baseline_execution_id` and
   `test_execution_id` of the first overlapping sample. Miqa creates one chain run per version; the comparison is the run
   for the test (newest) version.
7. Find the chain run(s) by chain name.

To change the block after it is created, or to apply an updated block to an existing run, read
`references/changing-the-block.md` first.

Basic assertions (fail type `warn`):
`{"file_collection": {"report": true, "checks": [{"name": "Outputs should have at least 1 file", "check_type": "file_collection", "stat": "data.total_count > 0", "detail_display_stat": "data.total_count", "failtype": "warn"}]}}`

## Q3. Say it is done, right away

Before any results check:
- Copy the new **test chain** link (`.../test_chain/<id>`) to the clipboard with `pbcopy` (macOS). If that fails, just
  print it.
- Print a short "done" message: what was created and every link the server returned (versions, group, block, chain, chain
  runs). Say that the results check and the report page are next. Do not wait for the user.

## Q4. Recheck the results (automatic)

- Read the run environment for the test run: every sample's execution should be Done.
- Read the run results. If the summary is still generating, retry up to 3 more times with a short wait between (say
  "retrying, n of 4" each time); then continue with the result marked pending. Do not loop longer. Foreground `sleep` may
  be capped; if it is blocked, just retry the call.
- Judge results only by what the server reports. If a check errors or reports FAIL, say so plainly and offer a corrected
  new block; never edit existing ones.

## Q5. Publish the report page (private, automatic)

Load `artifact-design`, then build the page from `report-template.html` in this skill's folder: copy it to the
scratchpad, replace the `{{...}}` placeholders and delete any section that does not apply, then publish with a
`report` icon. Publish even when the result is pending. Use the plain words the server returned; no invented success.

Finish with a short terminal message: the result as reported (or pending), the report link, and the next step.

## Q6. Next step

If only the basic check was used: say the test exists and can be opened now, and ask whether they want to build checks
around their actual data (suggest some, or paste requirements). If they pick requirements, hand off to
`assertion-translator` (draft from what they describe, using the executions just created), and prove what it drafts as
in `references/proving-checks.md`. Create nothing until the user confirms. Never start this unprompted.

---

# Step-by-step mode

Show what each stage will create and wait for a yes before it writes. Report every link the server returns.

1. **Check the samples.** List the pipeline's datasets and match the names. Report matches and unmatched names.
   Unmatched names stop here until the user says to create them (stage 3) or fixes the names.
2. **Offline version and executions.**
   - Read the pipeline's workflow variants (the offline-version-options operation) and pick the default or ask.
   - Create an offline version with a name the user chooses. Suggest one with the date. This is a write. With two
     versions, create the baseline first, then the test version.
   - Create one execution per matched sample on that version, passing each sample's output bucket, folder and
     optional prefix. Unmatched names come back and must be reported. The executions mark themselves complete from
     the output location, so a location the server cannot read will fail there; say so if one does.
3. **Create missing datasets (optional).**
   - Read the pipeline's dataset schema (the upsert-schema operation) before creating anything. It lists the metadata
     fields and the file slots.
   - Prompt the user for each sample's value for each metadata field. If the schema does not mark which fields are
     required, ask for all of them and allow blanks. Do not invent values.
   - Datasets for offline runs need no files. Do not ask for file paths unless the user wants them.
   - Create the datasets, then redo stage 2 for the new names.
4. **Dataset group (optional).** Create a group from the matched datasets with a name the user chooses, and return its
   link. A test over several samples needs this, because a test block built from one execution alone makes a
   one-sample group.
5. **Test (optional).** This creates a test block, a test chain and a chain run built from the executions, so the
   executions end up in a chain run. Always pass the group from stage 4 and one execution; the run picks up every
   sample's execution in the group for that version. With two versions, pass the baseline and test execution of the
   first overlapping sample together. Choose one:
   - **Minimal.** One file-count check. Ask for the file pattern and the expected count per sample; suggest the
     pattern from what the user said the outputs are. Never guess a count. Format:
     `{"file_counts": {"report": true, "checks": [{"name": "...", "check_type": "file_counts", "failtype": "fail",
     "file_rules": {"pattern": "..."}, "exp_val": 1, "relationship": "eq", "id": "..."}]}}`.
   - **Copy a block.** Read the source block's current version (the one flagged current, not the newest) and pass its
     assertions with the new group. If any check compares with a baseline, say that with one execution it compares
     with itself and will always pass; a real comparison needs a baseline execution and a test execution, passed
     together.
   - **From a request.** Use the `assertion-translator` skill to draft the assertions from what the user describes,
     prove them as in `references/proving-checks.md`, show them, then create the block with them.
   - **Use an existing block directly** is not supported. It needs a route that does not exist yet. Say so, and offer
     the options above instead.
6. **Check the result.** Read the new chain run's environment: every sample's execution should appear with status
   Done. Then read the run's results and report each check's status. The results may still be generating; retry
   shortly and say so if it is not ready. Do not report a run as passing before the results say so.

---

## Reporting

Terminal first: what was created (ids and links), what was not (unmatched names, skipped stages), and what the run
shows. Say what you did not test. If something fails, say which stage and quote the server's message.

## Never

- write anything before the user has confirmed (the single confirmation in quick mode, each stage in step-by-step), or
  beyond what the plan listed;
- invent metadata values, file patterns, expected counts, output locations or sample-to-folder matches, or match
  folders to samples silently;
- delete or change existing datasets, groups, blocks, chains or versions. This skill only creates;
- save a check that errored when it was run, or call a check verified beyond what actually ran;
- report a run as passing, or executions as complete, that the server has not reported so;
- run a test over several samples without a group;
- go quiet through a slow step;
- install packages to read an input file.
