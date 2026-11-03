# Proving checks before saving them

Read this before drafting or saving any check beyond the basic one (quick mode, Checks step).

This applies to checks drafted with `miqa:assertion-translator`. A schema validator only checks syntax; it does not run
the expression, so a check can validate cleanly and still error or never fail. Run every drafted check with the ad-hoc
assertion run (nothing is saved) on real executions first.

**Order of the runs (two versions).**
1. **Self-self first, on all assertions.** Take the first sample's baseline execution and use it as both baseline and
   test, with every drafted check plus the sentinels. This is the happy path. If anything errors or comes back incomplete
   here, fix it before going on (check the group names first). The only exception is a check built for a static baseline
   that has different files from the test, where the check already accounts for that.
2. **The first sample, baseline against test.** Use that sample's execution in the baseline version as the baseline and
   its execution in the test version as the test. Not everything has to pass, but there should be no errors and nothing
   incomplete.
3. **A second sample, baseline against test.** Pick another sample from the same set **at random** and say which one you
   picked. Again use that sample's own baseline-version and test-version executions. Same expectations as step 2. Never
   use one sample as the baseline and a different sample as the test; Miqa refuses.

**One version.** There is one set of executions. Use the same execution as baseline and test for every run, on the
first sample and on a second sample chosen at random (this is the self-self run). Comparative checks pass by
construction, so steps 2 and 3 above do not apply and no sample differs between versions; say that comparative checks have not
been shown to fail on real data. The sentinels still must fail.

You will not know which samples are supposed to pass or fail, so use controls with known answers as well:

- **Sentinel (must fail):** one always-false check for each check type used, for example `data.files.count < 0` (file
  collection), `data_baseline.files.count == -1` (paired), `data.rows.count < 0` (tabular). If a sentinel does not fail,
  that check type cannot gate. Stop and report it.
- **Identity (must pass):** run each comparative check with the same execution as both baseline and test. A comparative
  check that fails against itself, or comes back incomplete, is not proven. If it comes back incomplete, check that each
  group is named after its check type (see the expression notes below).
- **A sample that visibly differs between versions (should fail), when one exists:** you cannot compare two different
  samples (Miqa refuses with "Datasets do not match", even with `force_compare`), so look for a sample whose files
  differ between the baseline and test versions without any domain knowledge: compare the file counts (the run's
  execution stats, or the folder listing) for every sample. A sample with different counts must make a "same files"
  check fail. If no sample differs, say the check has not been shown to fail on real data.

Accept a check only if: it produced no evaluation error on any run, it passed the identity control, and its sentinel
type failed. If an expression errors, read the message, fix the expression and rerun. Do not save a check that errored.
Also read the per-check result, not just the overall status: a comparative check can come back "incomplete" with no value
when the pair is not comparable.

Report per check what was shown, not that it is correct: the first sample's outcome, the second sample's outcome, the observed value (from the
detail), and flags such as "never seen failing" or "passed on a sample whose files differ". A check that passed everywhere ran clean
but has not been shown to catch anything. Say so. Checks that are held back are listed with the reason, and saved only
after a new ask. If the user gave expected outcomes, use them as extra known-answer tests.

## Expression notes

Behavior can differ between deployments and documentation versions, so confirm each expression with an ad-hoc run
before saving it.

- **Name each group after its check type.** Comparative checks belong in a group named for their check type:
  `paired_file_collection` checks in `paired_file_collection`, `paired_tabular_mdo_eval` checks in
  `paired_tabular_mdo_eval`, `file_collection_compare` checks in `file_collection_compare`. In a group with another
  name, a comparative check can come back "incomplete" with empty results, and an always-false sentinel cannot fail. A
  paired check placed in a `file_collection` group reports "This was not an expected check type", and an always-false
  sentinel in it wrongly passes. If a comparative check is incomplete, check the group name first.
- `.sort()` sorts in place and returns nothing, so `list.sort() == list.sort()` **always passes**. To compare file names
  regardless of order use `data_baseline.files.map('basename').sorted_alphabetically() == data_test.files.map('basename').sorted_alphabetically()`
  (the `sorted(...)` builtin also works). Both fail on a sample with a missing file and pass on an identical comparison.
- Same file sizes: `data_baseline.size_by('basename') == data_test.size_by('basename')`.
- Aggregates on a mapped column are properties, not calls: `data.rows.map('col').min`, `.max`, `.mean`, `.sum`,
  `.median`, `.unique`. The called forms (`.min()`) return no result.
- `.length` and `.is_unique` can return no result on a mapped tabular column; avoid them unless an ad-hoc run confirms
  they work.
- A boolean stat hides the number. Bind the value in `_precompute` and set `detail_display_stat` to it.
- These work: `data.has_sibling_files('.bam', ['.bam.bai'])`, `data.files.with_size_less_than(1).count`,
  `data.files.with_extension([...]).count`, `data.files.map('extension').unique`, `files.frequency('extension')`.
- Paired checks use `"versions": [-1]` and compare with the previous version of the same sample.
- Prototype queries (`count_files`) can return 0 for patterns that should match. Do not use them to judge a check.
