# Changing the test block after it is created

- `update_test_block` replaces the block's assertions in full. It takes effect at once, has no preview, and creates a new
  block version on every call, even if the content is unchanged. Earlier versions stay in the block's history. Show the
  user the proposed assertions first (for example as an Output Explorer preview) and update only after they agree.
- To apply the updated block to an existing run, recheck the block run (or the chain run). The recheck re-evaluates the
  run against the newest version of the block. Rechecks run in the background and the results summary can take a few
  minutes to regenerate, so read the results again after it finishes before saying what changed.
- `set_test_block_run_version_overrides` changes which earlier run a comparative check compares against. It does not
  change the block version a run uses.
- `create_test_block` with `create_through: "chain"` creates a new chain. It does not add a block to an existing chain.
