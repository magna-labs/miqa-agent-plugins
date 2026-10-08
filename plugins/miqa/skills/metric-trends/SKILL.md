---
name: metric-trends
description: Use when the user wants to understand how Miqa metrics changed over time — "how has X changed across versions", "when did this metric move", "show me the history/trend of these results", "how much does this vary run to run", "chart these over builds", or wants historical values summarized or visualized for a pipeline, test chain or test block (via a connected Miqa MCP server). Pulls the history, cleans it, summarizes each metric (range, variation, where it changed), investigates a change on request, and offers a chart. Not for a single build's results (use version-rollup) or a trigger's current health (use active-triggers).
metadata:
  version: 0.1.0
---

# Miqa Metric Trends

Answers "what did this metric do over time, and why" for any set of Miqa
metrics: execution status and duration, Test Chain assertion results, and
optionally postprocessor results. It is a vertical slice through versions
for chosen metrics, where `version-rollup` is a horizontal slice across one
build and `active-triggers` is the current health of a trigger.

This skill calls `get_all_metrics` (it may appear as `api_get_all_metrics`)
on whichever Miqa MCP server is connected (tool names follow the pattern
`mcp__<server-name>__<tool>`). If more than one Miqa server is connected,
ask which one before proceeding.

It describes what happened. It does not choose pass/fail thresholds unless
the user asks (step 7), because the usual reason for asking is to look at
the history before deciding.

## Prerequisite: check the tool exists

`get_all_metrics` is newer than most of the Miqa MCP tools, and not every
environment has it yet. Before doing anything else, look for it among the
connected server's tools (as `get_all_metrics` or `api_get_all_metrics`,
searching deferred tools too if your client defers them). If it isn't
there, stop and tell the user plainly and kindly that metric history isn't
available on their Miqa environment yet, that it needs a newer Miqa
deployment, and that Miqa support (or whoever administers their Miqa
environment) can enable it. Don't guess a different tool name, and don't
quietly rebuild the history from per-run tools: that is slow, partial and
easy to get wrong. If the user still wants a limited version, say what it
would cost (one lookup per run, only recent runs) and let them choose.

## Pacing: this can be slow, so go in stages

The assertion query reads stored results for every run it covers, and a
wide window means a large response, so a full history can take a while and
is heavy to read. Work in stages and keep the user informed:

- Say what you are about to fetch before you fetch it, and run the
  independent calls (assertions and execution status) in parallel.
- Start with a bounded window (the default newest 25 versions) unless the
  user asked for the full history. Widen only if the first pass shows they
  need more, and say so when you do. The window is pipeline-wide, so a
  chain that ran in only a few of those versions yields very little: if
  the first pass has fewer than about 10 completed runs, widen straight
  away instead of summarizing it.
- If a call is slow or times out, retry narrower (fewer versions, or a
  `metric_parent` or `tc_ids` filter) rather than repeating the same call.
- Compute the statistics and plateaus with code on the saved response
  rather than reading rows by eye, and keep large raw output out of the
  main conversation (a subagent or a script is fine).
- Ship the terminal summary (step 5) before any investigation, and before
  any chart; never build the chart in the same step as the first answer.

## Procedure

1. **Establish scope and org.** Call `get_org_context` first; if the user
   has several orgs and none is selected, ask once, then `set_organization`.
   Resolve what they mean by name: a pipeline (`get_pipelines`), a test
   chain, or a test block. Test chain ids can be passed as `tc_ids` and the
   pipeline is then taken from them; otherwise pass `pipeline_id`. Ask only
   if the scope is genuinely ambiguous.

2. **Pull the history with `get_all_metrics`, one source per call.**
   - Assertions: `metric_category=test_assertion`, plus `tc_ids` and/or
     `metric_parent` (a case-insensitive substring of the test block name)
     to keep the response small.
   - Status and duration: a separate call with `metric_category=execution`.
     You need it to know which versions actually completed.
   - Postprocessor values only when asked: `include_pp_results=true`.
   - Choose `limit` deliberately. The default is the newest 25 versions;
     `limit=0` is every version and can be large (the version window is
     pipeline-wide, not per chain), so use it only when the user wants the
     full history and keep each call to one category.
   - Pass `version_field` (a `component_info` field such as the docker tag)
     if you know it; versions without that field fall back to the bare id.
   - If a response is empty, say which filter or scope probably caused it
     (wrong chain, over-narrow `metric_parent`, no accessible pipeline)
     instead of guessing.

3. **Read the shape correctly.** Each row is one metric for one dataset;
   every key other than the fixed fields (`datasource_id`, `metric_parent`,
   `metric`, `value_type`, `metric_category`) is a version holding that
   value. A version missing from a row has no value; never treat it as
   zero. Then normalize before computing anything:
   - Assertions appear as two rows: `<assertion>|result` is the measured
     value and `<assertion>|outcome` is pass/fail. Use `|result` for value
     trends and `|outcome` for pass/fail history.
   - The threshold is part of the metric name (`SNP F1 >= 0.9786|result`),
     so history splits when a threshold was edited. Strip the comparison
     (`[<>]=?\s*number`) from the name and merge rows that now share it.
   - Rows can appear in duplicate, including empty twins; merge them and
     check that merged cells don't disagree.
   - Drop versions whose execution status isn't `Done` before computing
     anything; a failed or unfinished run has no real value. Very long
     durations on failed runs (a repeated figure like 43,200s) look like
     timeouts. Keep them on the chart as gaps so a change hidden behind a
     run of failures is visible.
   - Each workflow variant is a separate series. Say so when a variant has
     no data instead of silently omitting it.
   - Label versions by docker tag and build date (a `yymmdd` in the tag
     usually is one), never by an internal id or `v###` number. If a
     version has no docker tag (the label falls back to the bare id), use
     its id, say it has no tag and no build date, and place it by order
     between its neighbours.

4. **Summarize each metric.** For every dataset, variant and metric: count,
   min, max, mean, standard deviation, number of distinct values, and a
   short characterization. Group consecutive runs with identical values
   into plateaus and report where each begins. Say explicitly whether the
   metric moves in steps (deterministic pipeline, changes come from code or
   data changes) or varies run to run (real noise); the answer changes
   what the numbers mean. Report absolute spread always, and relative
   spread only for counts or values far from zero — for ratios and
   anything near zero a tiny absolute change looks like a large percentage.

5. **Post a terminal table first** — don't investigate or chart before
   shipping it. One row per metric (grouped by dataset): range, spread,
   distinct values, number of plateaus, latest value. Note that this
   terminal renders plain CommonMark: no cell color and no inline links.
   End with the open questions you could not answer from the data.

6. **Investigate a change, only when asked or clearly wanted.** Find the
   first version showing the new value and the last showing the old one.
   If failed runs sit between them, say the change is bounded but not
   pinpointed and name that window. Look at what differed between those
   builds (`get_test_chain_run_environment`, component version listings for
   the runs on either side) and say plainly what is evidence and what is
   inference. A "baseline comparison" style assertion failing on the first
   run of a plateau is supporting evidence that the change was detected at
   that point, not proof of its cause. Don't name a cause you haven't seen.

7. **Thresholds, on request only.** If the user asks what should warn or
   fail, give the options and their consequences rather than a single
   answer, for example: a tolerance around the current plateau, a band
   covering the whole observed range, or an exact match for a
   deterministic metric. State which historical runs each would have
   flagged, and use absolute tolerances for ratios and near-zero values.
   The decision is theirs.

8. **Chart on request only.** After the table, mention once that a chart
   is available (same offer pattern as `active-triggers`: state it once,
   don't re-offer, don't publish without a yes). When they accept, publish
   a private Artifact:
   - The step 5 summary table at the top, with the same columns.
   - One small chart per metric on its own absolute scale, versions on
     the x-axis labelled by date, failed runs shown as gaps or ticks (never
     as zeros), and the min/max labelled. Leave plateau shading off any
     stretch hidden behind failed runs, so a change bounded by failures
     reads as bounded.
   - Shade each plateau by direction from the previous one, with a ▲ or ▼
     and the signed change, so subtle steps are visible. This is direction
     only, not better or worse, unless you know which way is good for that
     metric.
   - A companion distribution panel per metric on the same y-scale as the
     trend, chosen by the shape found in step 4:
     - Plateau-shaped (few distinct values, say 8 or fewer, mostly
       repeats): run-count bars at each distinct value. Nudge bars apart
       where values nearly coincide and keep a line to the true height.
     - Varies run to run (many distinct values): a histogram plus a box
       plot (min, quartiles, median, max, outliers marked), and no plateau
       shading, since there are no plateaus.
     - Mixed (steps with noise inside each step): a box plot per plateau.

   Every plotted number comes from the pulled data. The user decides
   whether to share the link; don't claim it was shared.

## Notes

- The tool returns only metrics that exist on the chosen scope. If a metric
  the user names is absent, check the metric name before the scope: renamed
  assertions and edited thresholds both change the name.
- Memory or earlier-session claims about a metric's history are leads,
  never citable facts; re-pull before repeating them.
- For very wide results (many datasets or variants), summarize per dataset
  and offer to expand one, rather than printing everything.
