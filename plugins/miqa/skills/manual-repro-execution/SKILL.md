---
name: manual-repro-execution
description: Use whenever a user wants a known-bad output file (a bug repro attachment, a hand-crafted edge case, a customer-supplied sample) turned into a real Miqa execution so a check can be proven against it — not a routine pipeline run. Trigger phrases include "attach this bug's file as a manual execution", "add this repro to Miqa and test it", "create a regression test from this ticket's attachment", "upload this sample and check it against BTR-1". Creates a one-off manual-upload ComponentVersion, an execution against the right dataset, uploads the file via signed URL, verifies the relevant check against it, then wires the check into a Test Block — asking the user at every genuinely case-specific fork (which pipeline/dataset, which check to reuse, which Test Block) rather than guessing.
metadata:
  version: 1.1.0
---

# Manual Repro Execution

Turn a known-bad file into a real, checkable Miqa execution. This is not a
routine pipeline run — nothing actually executes; you upload a file
directly as if a pipeline had produced it, so a check can be proven against
concrete bad data instead of only against the good runs a trigger already
has.

This skill calls tools named `api_create_offline_version`,
`api_get_offline_version_options`, `api_get_pipelines`,
`api_get_pipeline_datasets`, `api_batch_manual_executions`,
`api_get_execution_output_signed_urls`, `api_complete_execution_output`,
`inspect_execution_outputs`, `api_run_adhoc_assertions`,
`publish_adhoc_assertions`, `api_get_test_block_version`, and
`api_update_test_block` on whichever Miqa MCP server is connected (tool
names follow the pattern `mcp__<server-name>__<tool>`). Most setups have
exactly one Miqa MCP server connected — just use it.

**The fiddly parts are mechanical and fixed** (the signed-URL upload
sequence, merging into an existing Test Block's assertions rather than
clobbering it). **The identity parts are not** — which pipeline, which
dataset, which existing check to reuse, which Test Block to land in all
vary by request and by deployment. Treat every one of those as a real fork:
resolve what evidence can resolve, ask the user for the rest. Never guess a
pipeline, dataset, or Test Block from a name pattern alone.

## Procedure

1. **Get the actual file before doing anything else.** If the source is a
   ticket (Jira or similar), check whether an attachment-download tool is
   actually available on the connected tracker MCP server — most
   configurations expose issue/page metadata and search only, with no
   attachment-content endpoint. When that's the case, tell the user
   plainly and ask them to download the attachment locally and give you
   the path, or paste its content directly. Never fabricate file content
   or proceed on the ticket's text description alone when an attachment
   exists — read the real file (`Read` for a local path) before drafting
   or reusing any check against it, so column/field assumptions are
   grounded in the actual data rather than the ticket's prose.

2. **Resolve the check.** If a check already covers this bug (e.g. a prior
   `assertion-translator` pass already drafted and published one, from
   this ticket or an adjacent request in the conversation), reuse it
   as-is — don't redraft. If no check exists yet, delegate to
   `assertion-translator` to draft one from the ticket/request; don't
   duplicate its translation logic here. Either way, you need the
   finished assertions blob before step 7.

3. **Find the pipeline.** Search `api_get_pipelines` by product/component
   name. Deployments commonly have several identically-named pipelines
   (demo scaffolding, old copies) — name collisions are the norm here, not
   the exception. Disambiguate using evidence, in order:
   - Signals inside the file itself (a command line, a tool-version
     header, an internal sample name) naming a specific dataset or
     parameter variant.
   - `api_get_offline_version_options(pipeline_id)` on candidates — a
     workflow-variant name matching a parameter the file's own metadata
     names (e.g. the file's command used `-Q 30` and one candidate has a
     `Q30` variant) is real evidence, not a coincidence to ignore.
   - If nothing distinguishes the candidates, ask the user which pipeline
     they mean. Do not default to whichever pipeline the conversation was
     already discussing — confirm it actually owns a matching dataset in
     step 4 first.

4. **Find the dataset — don't assume it's whatever dataset an existing
   Test Chain/Trigger under discussion already uses.** Call
   `api_get_pipeline_datasets(pipeline_id)` and match against evidence
   from the file (an internal sample name, a source filename referenced in
   a command/header line) rather than the name of a dataset already in
   play elsewhere in the conversation — they can genuinely differ, since a
   bug repro file may come from a different sample than the pipeline's
   regular test data. If nothing in the file points to a specific dataset
   name and more than one plausible match exists, ask the user.

5. **Create the one-off version and execution.**
   `api_create_offline_version(pipeline_id, name, wfv_id)` — name it so
   it's identifiable later (reference the ticket/bug, not just "manual
   upload"). Show the returned `statemachine_url`. Then
   `api_batch_manual_executions(sm_id, items=[{name: dataset_name}])`
   using the dataset confirmed in step 4. If the name comes back in
   `not_found_names`, don't retry with a guessed variant — re-check
   `api_get_pipeline_datasets` for the actual name or ask the user.

6. **Upload the file and confirm Miqa recognized it.** Name the upload
   filename to match the `file_rules.pattern` the check from step 2
   expects (e.g. an assertion matching `.*\.vcf$` needs a filename ending
   `.vcf`), not the file's original name if that name wouldn't match.
   `api_get_execution_output_signed_urls(execution_id, filenames)`, PUT
   the file's bytes to each returned URL yourself (`curl -X PUT
   --data-binary @path url`, or equivalent), then
   `api_complete_execution_output(execution_id, keys)`. Confirm with
   `inspect_execution_outputs(execution_id)` that the expected file type
   was recognized before moving on — an unrecognized upload fails silently
   downstream (the check just won't find a matching file) rather than with
   a clear error here.

7. **Verify the check against the new execution by reading the actual
   computed outcome, not just publishing and eyeballing the UI.** This
   file is a *known-bad* repro, so the check must come back `fail` (or
   `warn`, matching the drafted `failtype`) — a `pass` on a known-bad file
   means the assertion is wrong, not that the bug failed to reproduce.
   Call `api_run_adhoc_assertions(assertions, exec_ids_test=[execution_id],
   force_recheck=true)` and read `outcome`/`status` straight out of its
   JSON — it's synchronous and persists nothing, so there's no reason to
   infer the result from a preview or a UI link instead. When the outcome
   doesn't match the known-bad expectation, don't just report the
   mismatch: a check's declarative pass/fail direction for
   `stat {relationship} threshold` is not guaranteed the same across check
   types (verify it from this actual response, never assume it from
   another check type's docs or blurb), so fix the `relationship`/
   `threshold` and re-run `api_run_adhoc_assertions` until the outcome
   matches, before calling `publish_adhoc_assertions(apply=true)` with the
   corrected blob. When the check's logic is simple enough to hand-verify
   from the file you already read in step 1 (e.g. an average of a handful
   of visible values), compute the expected result yourself and state it
   alongside the outcome — that catches a wrong column/field assumption
   (e.g. two same-named fields at different structural levels, like a
   VCF's INFO-level vs. FORMAT-level `DP`) that schema validation can't.
   If the logic is too complex to hand-verify, ask the user to confirm the
   outcome is what they'd expect before treating it as done. Only then
   show the Output Explorer link from `publish_adhoc_assertions`.

8. **Ask where the check should live — don't assume.** If the check is
   already permanently wired into a Test Block (e.g. from a prior
   `assertion-translator` + apply pass), say so and stop; don't create a
   second copy. Otherwise ask the user: fold it into an existing Test
   Block (fetch the current version's assertions with
   `api_get_test_block_version` first — `api_update_test_block` is a full
   replace, not a merge, so missing checks silently disappear — then
   `api_update_test_block` with the merged blob), or create a new
   standalone one via `api_create_test_block`. The right answer depends on
   whether this bug belongs in the pipeline's regular coverage or should
   stay an isolated regression fixture — that's the user's call, not a
   default.

## Notes

- Manual executions themselves are fine to create without asking first
  (they don't start real pipeline work) — but `api_update_test_block` has
  no dry-run and mutates shared, shared-pipeline configuration immediately,
  so get explicit confirmation before that specific call, same as any
  other Test Block edit.
- If the ticket names more than one attachment or repro case, resolve them
  one at a time rather than batching blindly — a wrong dataset/pipeline
  guess on one shouldn't silently propagate to the others.
- This skill produces real, permanent Miqa resources (a pipeline version,
  an execution, possibly a new Test Block) — it is not a scratch/ad-hoc
  preview the way `assertion-translator`'s own publish step is. Say so
  when reporting back.
