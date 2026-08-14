# miqa-agent-plugins

## Claude Code
Claude Code plugin marketplace for Miqa. Wires up the Miqa MCP server
(published on PyPI as `miqa-mcp`) and ships skills for working with it.

### Install

```bash
export MIQA_SERVER_URL=api.YOURSERVER.miqa.io
export MIQA_API_KEY=XYZ

claude plugin marketplace add magna-labs/miqa-claude-plugin
claude plugin install miqa@magna-labs
```

If Claude Code reports it needs a reload after install, run `/reload-plugins`.

## What's included

- **MCP server** — connects to your Miqa deployment via `uvx miqa-mcp`
  (see `plugins/miqa/.mcp.json`).
- **Skills**
  - `active-triggers` — sweeps enabled Miqa test triggers, flags which are
    actually active vs. dormant, and root-causes failures (real regression
    vs. stale baseline vs. still-running). Triggered by things like "what's
    going on with my active test triggers" or "why are my miqa triggers
    failing".
