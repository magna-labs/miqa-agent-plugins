---
name: fp-comparison
description: Use when the user wants to understand how the false-positive and false-negative variant calls and the precision and sensitivity of a variant-calling pipeline changed between builds, e.g. "why did indel precision drop", "did the new build fix the false positives", "compare the FPs and FNs between these two runs", "which calls did we start missing", "what kind of calls did the fix remove", "is precision or sensitivity driving this" (via a connected Miqa MCP server). Compares a later run with an earlier run and with their baseline: precision, sensitivity and F1 per sample, then the saved false-positive and false-negative tables (when the run keeps them), call by call, split by call type, size, repeat context, sample and genome region. Terminal summary first, then a private HTML page on request. Read-only. Names no cause.
metadata:
  summary: Explain how false positives, false negatives, precision and sensitivity changed between two builds and their baseline.
  version: 0.1.0
---

# False-Positive and False-Negative Comparison

Put three runs side by side: the baseline, an earlier build and a later build. Say how precision, sensitivity and F1
moved, and which false-positive and false-negative (missed) calls appeared, stayed or went away. It describes what the outputs show. It does not
say why a build behaves differently, and whether a change is acceptable is the owner's call. Nothing about any
particular pipeline belongs in this file.

## Tools

Tool names follow `mcp__<server>__<tool>`, and the gateway tools may carry an `api_` prefix: `list_test_chain_runs_for_trigger`,
`find_test_chain_runs_by_chain_name`, `get_test_chain_run_environment`, `get_test_chain_run_results`,
`list_test_chain_run_tables`, `get_test_chain_run_table`, `get_all_metrics`, `get_signed_url` and
`inspect_execution_outputs`. Call `get_org_context` first; on a hosted server `set_organization` is unavailable, so do
not claim which organization the data came from unless a tool said so.

## Inputs

The two runs to compare, as run ids, builds (docker tag or date) or "the latest and the one before". The baseline is
not asked for: read it from the runs (step 2). If only one run is named, compare it with the previous run of the same
chain and say so. Both runs must be of the same test chain.

## Procedure

1. **Confirm what ran.** `get_test_chain_run_environment` gives the workflow version name and the executions. Label
   builds by build date and commit, for example `261102-46d60a9`, taken from the workflow version name. The run
   listing and the metrics history label a run from the docker image record linked to its component version. That link
   can disagree with the image that ran when a version was edited in place or made as a one-off. When a label looks
   wrong or two columns share a tag, read one execution's steps log (`get_signed_url` for `_MIQA_STEPSLOG.txt`) and
   quote the image it ran. Say which source each label came from.
2. **Find the baseline.** The environment shows `default_baseline_tbr_id` and the status event's `baseline_used`.
   Those are test block run ids, not run ids: find the run that contains that block run by reading the environments
   of candidate runs. Read the baseline from each run, because two runs of one trigger can use different baselines. If
   the environment shows none, the checks may not have finished: wait and read it again before assuming one.
3. **Check results and per-sample numbers.** `get_test_chain_run_results` for both runs: which checks fail, warn or
   pass, and the aggregate values. `get_all_metrics` with `metric_category=test_assertion`, `include_pp_results=true`
   and `version_field=id` gives per-sample precision, sensitivity and F1 as `<check>|result` rows. Version columns are
   workflow version ids and can look alike, so match a run to its column by comparing the run's own aggregate values.
   The stored values have four decimals: say that a change below 0.0001 in one sample cannot show. Report real
   values and signed differences, never multiples of the last digit.
4. **Say whether precision or sensitivity moved.** Take the mean over samples for each statistic at the baseline, the
   earlier build and the later build, with signed differences. When the change is mostly in one of them, say so with
   the numbers. Precision moves with false positives and sensitivity moves with false negatives. Compare the share of the precision
   change that came back with the share of the false positives that went away, and the same for sensitivity and false
   negatives: when they agree, say they agree.
5. **Read the false-positive and false-negative tables.** `list_test_chain_run_tables` for each run. Look for the
   table of all false positives, the table of all false negatives if the run keeps one, and for each the table of
   calls that differ from the baseline (it carries an `overlap_status` column). A run may keep only false positives.
   Say which kinds exist for each run, and treat the two kinds separately from here on. Check the
   columns with a three-row read first, and ask only for the columns needed (sample, chromosome, position, REF, ALT,
   and any repeat columns). Read every page, 1000 rows at a time. The pages are saved to files: process them with
   code, with Python run as `python3 -I`, and never print rows. Check that the offsets are contiguous and that the row
   count equals the table's `total_rows`. Identical table ids on two runs suggest identical content, but compare the
   rows before saying so.
6. **Analyse with code.** Match calls on sample, chromosome, position, REF and ALT. Do everything below once for the
   false positives and once for the false negatives. For false negatives, "new" means missed on this run and not at the
   baseline, and "gone" means missed at the baseline and found now. Do not merge the two kinds into one total.
   - Per run: total, new against the baseline, gone against the baseline (from `overlap_status`). Both runs should
     reconstruct the same baseline total; if not, they use different baselines.
   - Classify each call: insertion, deletion or other from the allele lengths; size bucket; repeat unit (single base
     A or T, single base C or G, multi-base, none); repeat length from the repeat-count column, with the first value
     as the reference count; whether it is flagged as a short tandem repeat.
   - Against the baseline, for each run: the share of new calls that are insertions, against those that were already
     there; the share in repeats; per sample, new calls split into the dominant context and everything else; the
     share of each context that is new, by repeat length and by insertion or deletion.
   - Run against run: calls on both runs, only on the earlier, only on the later; the same cuts on the gone and new
     groups, with per-sample counts.
   - Checks on what the difference is: new calls within a few bases of a gone call in the same sample (a shifted
     position), gone and new calls at the same site (an allele swap), the share seen in more than one sample, and
     clusters in the genome (windows of 1 Mb against a Poisson expectation from the counts).
7. **Terminal summary first.** The check status, the mean precision, sensitivity and F1 table, the call counts (both
   runs and the baseline), the largest findings with numbers (false positives and false negatives each), and what was not compared. Then offer the deeper
   dives under "Go deeper" and a private page, once each.
8. **Page, on request.** A private HTML page: the count strip and check table, the precision and sensitivity table
   with a dot plot per sample on a common scale, the baseline view (one for false negatives too, when they exist) (callouts, share by repeat type, per-sample stacked
   bars, a heatmap of the share that is new by repeat length), the run-against-run view (flow bar, per-sample table,
   size chart, heatmap of the share that went away), a list of limits, and sources with run ids, table titles and the
   read date. Label builds with the date-prefixed tag. Use real sample names for the team and anonymize only if the
   user says the page goes outside. Say a published page is private until the user shares it.

## Go deeper

The checklist in step 6 is a start. Treat a finding as a lead and test the obvious alternative before reporting it.

- **When one group stands out, test the other.** If the calls that went away are a distinct kind (for example mostly
  one-base insertions in one repeat context), check whether the new calls are distinguishable from the background on
  size, repeat annotation, sample recurrence and region. Report both: "distinct" and "looks like the rest" are both
  findings.
- **When a number disagrees with what you expected, check a second source.** Two runs with identical tables, a run
  whose label does not match its image, a baseline that differs from the one assumed: confirm with the run
  environment, the results and an execution log before saying it.
- **Reconcile before explaining.** The change in false-positive counts, the change in precision and the per-sample
  numbers should tell the same story, and likewise false negatives with sensitivity. Say when they do and when they do not.
- **Follow a sample or region that stands out.** The sample with the largest change, a window with many changes, a
  group that recovers less than the rest: read a few concrete calls (position, alleles, context) and describe them.
- **Offer these after the summary, and run the ones the user picks:** compare quality or model scores of the gone,
  new and kept calls (this needs the tables read again with those columns); examine a single sample or window; put a
  third build alongside; split by repeat unit length or by call size; list example calls. Name each with what it
  needs, so the user can choose.

Keep every deep dive to what the data shows. A pattern is a pattern, not a cause.

## Say plainly

- the baseline each run used and how it was found;
- which label came from which source when they disagree;
- matching is exact on position and alleles, so a call written at a shifted position counts as one gone and one new;
- when a run keeps no false-negative table, a change in sensitivity cannot be traced to calls, and the page says so;
- quality scores are not compared unless they were pulled;
- each build was run once, so run-to-run noise is not measured;
- a cause for any difference is not established by this comparison.

## Never

- change, rebaseline, retry or create anything. This skill is read-only;
- name a cause, or say a change is expected or fixed unless told;
- present a difference as a multiple of a unit instead of real values;
- print table rows or whole result files into the conversation;
- compare runs of different test chains.
