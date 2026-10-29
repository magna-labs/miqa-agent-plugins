---
name: offline-runs-to-test
description: Use when the user has results from runs that happened outside Miqa and wants them in Miqa, e.g. "I have outputs for these samples in a bucket", "bring these offline runs into Miqa", "set up executions for these samples", "start from these output folders and make a test" (via a connected Miqa MCP server). Takes a list of samples (or an existing dataset group) with where each sample's outputs live. Creates an offline version and one execution per sample, and can go on to create missing datasets, a dataset group, and a test block, chain and linked chain run. Asks what the pipeline requires for dataset metadata. Writes only after confirmation.
metadata:
  summary: From samples and output locations to executions, a group and a passing test.
  version: 0.1.0
---

# Offline Runs to Test

Start from outputs that already exist and go as far as the user wants: executions only, executions in a dataset group,
or all the way to a test block, a chain and a chain run that contains every sample's execution. Everything specific
(pipeline, field names, file patterns) comes from the user or from the server. Nothing about any particular pipeline
belongs in this file.

Tool names differ between deployments (some carry an `api_` prefix). This file names the operations in words; use
whichever tool name the connected server offers. Call `get_org_context` first where it exists.

## Inputs

- **The pipeline.** The user gives the id or name. Otherwise read it from a dataset: the dataset detail lists its
  pipeline ids. The list-pipelines operation may be missing on older backends; do not rely on it.
- **The samples**, either as a list of names or as an existing dataset group (list its datasets).
- **Where each sample's outputs are:** bucket and folder, optionally a file prefix. One location can be shared by all.
  If the user points at an existing run, read its locations from that run's environment (the run-environment
  operation) and split the combined `bucket/folder` string at the first slash. Do not use the run-details operation to
  read it; it can fail with an output validation error on some servers.
- **How far to go:** executions only, plus a group, or through a test. If the user does not say, do executions and
  ask whether they want a group and a test.

## Procedure

Show what each stage will create and wait for a yes before it writes. Report every link the server returns.

1. **Check the samples.** List the pipeline's datasets and match the names. Report matches and unmatched names.
   Unmatched names stop here until the user says to create them (stage 3) or fixes the names.
2. **Offline version and executions.**
   - Read the pipeline's workflow variants (the offline-version-options operation) and pick the default or ask.
   - Create an offline version with a name the user chooses. Suggest one with the date. This is a write.
   - Create one execution per matched sample on that version, passing each sample's output bucket, folder and
     optional prefix. Unmatched names come back and must be reported. The executions mark themselves complete from
     the output location, so a location the server cannot read will fail there; say so if one does.
3. **Create missing datasets (optional).**
   - Read the pipeline's dataset schema (the upsert-schema operation) before creating anything. It lists the metadata
     fields and the file slots.
   - Prompt the user for each sample's value for each metadata field. If the schema does not mark which fields are
     required, ask for all of them and allow blanks. Do not invent values.
   - Datasets for offline runs need no files. Do not ask for file paths unless the user wants them.
   - Create the datasets, then redo stage 2 for the new names. (Untested: this stage has not been run end to end.)
4. **Dataset group (optional).** Create a group from the matched datasets with a name the user chooses, and return its
   link. A test over several samples needs this, because a test block built from one execution alone makes a
   one-sample group.
5. **Test (optional).** This creates a test block, a test chain and a chain run built from the executions, so the
   executions end up in a chain run. Always pass the group from stage 4 and one execution; the run picks up every
   sample's execution in the group for that version. Choose one:
   - **Minimal.** One file-count check. Ask for the file pattern and the expected count per sample; suggest the
     pattern from what the user said the outputs are. Never guess a count. Format:
     `{"file_counts": {"report": true, "checks": [{"name": "...", "check_type": "file_counts", "failtype": "fail",
     "file_rules": {"pattern": "..."}, "exp_val": 1, "relationship": "eq", "id": "..."}]}}`.
   - **Copy a block.** Read the source block's current version (the one flagged current, not the newest) and pass its
     assertions with the new group. If any check compares with a baseline, say that with one execution it compares
     with itself and will always pass; a real comparison needs a baseline execution and a test execution, passed
     together. (Untested.)
   - **From a request.** Use the `assertion-translator` skill to draft the assertions from what the user describes,
     show them, then create the block with them. (Untested.)
   - **Use an existing block directly** is not supported. It needs a route that does not exist yet. Say so, and offer
     the options above instead.
6. **Check the result.** Read the new chain run's environment: every sample's execution should appear with status
   Done. Then read the run's results and report each check's status. The results may still be generating; retry
   shortly and say so if it is not ready. Do not report a run as passing before the results say so.

## Reporting

Terminal first: what was created (ids and links), what was not (unmatched names, skipped stages), and what the run
shows. Say what you did not test. If something fails, say which stage and quote the server's message.

## Never

- write anything before the user has confirmed that stage;
- invent metadata values, file patterns, expected counts or output locations;
- delete or change existing datasets, groups, blocks or chains. This skill only creates;
- report a run as passing, or executions as complete, that the server has not reported so;
- run a test over several samples without a group.
