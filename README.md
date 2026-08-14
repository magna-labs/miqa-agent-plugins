# miqa-agent-plugins

Agent integrations for Miqa. Currently supports Claude Code; more agents
(e.g. Codex) coming soon.

## Claude Code

Claude Code plugin marketplace for Miqa. Wires up the Miqa MCP server
(published on PyPI as `miqa-mcp`) and ships skills for working with it.

### Prerequisites

- Claude Code (v1.0.33+)
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) installed
  — the MCP server runs via `uvx`, so this needs to be on your `PATH`
  before installing:
  ```bash
  brew install uv
  # or: pip install uv
  ```
- A Miqa APIv2 key — create one at {your_miqa_server}/manage_app_keys_v2/
  (click **Add+**, then copy the value)

### Install

```bash
export MIQA_SERVER_URL=api.YOURSERVER.miqa.io
export MIQA_API_KEY=key_from_above

claude plugin marketplace add magna-labs/miqa-agent-plugins
claude plugin install miqa@magna-labs
```

If Claude Code reports it needs a reload after install, run `/reload-plugins`.

**Verify it worked:**
```bash
claude mcp list        # should show "miqa-aws" (or your configured server name)
```
Type `/` in a session — you should see `/miqa:active-triggers` in the list.

### What's included

- **MCP server** — connects to your Miqa deployment via `uvx miqa-mcp`
  (see `plugins/miqa/.mcp.json`).
- **Skills**
  - `active-triggers` — sweeps enabled Miqa test triggers, flags which are
    actually active vs. dormant, and root-causes failures (real regression
    vs. stale baseline vs. still-running). Triggered by things like "what's
    going on with my active test triggers" or "why are my miqa triggers
    failing" — or invoke it directly with `/miqa:active-triggers`.
  - `assertion-translator` — translates Python analysis scripts or
    natural-language requirements into validated Miqa Output Explorer
    assertions and a coverage report.

### Usage examples

```
rebaseline Variant Calling Test from the run for 1.0.0-a1b2c3
run /miqa:active-triggers
miqa trigger status
```

### Uninstall

```bash
claude plugin uninstall miqa@magna-labs        # remove just the plugin
claude plugin marketplace remove magna-labs    # remove the marketplace entirely
```

### Troubleshooting

- **MCP server not showing up in `claude mcp list`** — most often means
  `uv`/`uvx` isn't installed, or `MIQA_SERVER_URL`/`MIQA_API_KEY` weren't
  set *before* running `claude plugin install`. Set them and reinstall.
- **"Plugin not found in marketplace"** — your local marketplace cache may
  be stale; run `claude plugin marketplace update magna-labs` and retry.
- Still stuck? Ping help@magnalabs.co (or open an issue in this repo).
