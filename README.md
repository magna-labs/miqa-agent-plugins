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

`MIQA_SERVER_URL`/`MIQA_API_KEY` are only read when the MCP server process
starts. If you rotate your API key or point at a different Miqa
deployment later, re-export the new values and restart Claude Code (or
run `/reload-plugins`) — there's no hot-reload.

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

### Update

```bash
claude plugin marketplace update magna-labs    # pull the latest marketplace metadata
claude plugin update miqa@magna-labs           # update to the latest published version
```
Restart Claude Code (or run `/reload-plugins`) afterward to pick up the update.

**Check what version you have installed:**
```bash
claude plugin list                       # installed plugins and their versions
claude plugin details miqa@magna-labs    # this plugin's version + component inventory
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
- **SSL error connecting to Miqa** (e.g. `self-signed certificate in
  certificate chain`) — common on corporate/managed laptops behind a
  TLS-inspecting VPN or proxy. `uvx` runs the MCP server in an isolated
  Python environment that validates certs against its bundled `certifi`
  CA list, not your OS trust store — so an org root CA that's trusted
  system-wide (browsers, `curl`) may still be untrusted here. Fix: get
  your org's root CA cert, then set `SSL_CERT_FILE` (or
  `REQUESTS_CA_BUNDLE`) to its path before starting Claude Code, e.g.
  ```bash
  export SSL_CERT_FILE=/path/to/corp-root-ca.pem
  ```
- Still stuck? Ping help@magnalabs.co (or open an issue in this repo).
