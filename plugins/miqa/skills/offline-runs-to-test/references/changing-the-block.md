# Changing the test block after it is created

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
