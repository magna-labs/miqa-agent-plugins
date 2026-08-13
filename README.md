# miqa-claude-plugin

Claude Code plugin marketplace for Miqa. Wires up the Miqa MCP server
(published on PyPI as `miqa-mcp`) and ships skills for working with it.

## Install

```bash
export MIQA_SERVER_URL=api.awstest.magnalabs.co
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

## Releasing a new version

When `miqa-mcp` ships a new PyPI version:

1. Bump the version pin in `plugins/miqa/.mcp.json` (the `miqa-mcp@X.Y.Z` arg).
2. Bump `version` in `plugins/miqa/plugin.json`.
3. Bump `version` in `.claude-plugin/marketplace.json`.
4. Commit and push.

Users pick up the update with:

```bash
claude plugin marketplace update magna-labs
claude plugin update miqa
```

## Repo layout

```
.claude-plugin/
  marketplace.json       # catalog entry for the "miqa" plugin
plugins/
  miqa/
    plugin.json           # plugin manifest
    .mcp.json              # MCP server config (points at published miqa-mcp)
    skills/
      active-triggers/
        SKILL.md
```
