# Startup Context Server

The shared context plane for Decentralized-Network. It offers:

- **GraphQL** at `/graphql` for applications and dashboards.
- **MCP over stdio** for repository-local clients: OMP, Claude Code, Cursor, Gemini CLI, and compatible editors.
- **Streamable HTTP MCP** at `/mcp` for remote MCP clients after deployment.

An AI client must be configured to use an MCP server; no service can inject context into models that do not support or connect to MCP.

## Architecture

```text
docs/*.md + src/data.ts ──> resolvers.ts ──> GraphQL /graphql
                                            MCP stdio (mcp.ts)
                                            MCP HTTP /mcp
```

`data.ts` holds structured startup facts. The resolver indexes all Markdown under `docs/` at startup, so `get_doc`, `list_docs`, and `search_context` reflect the tracked documents without a second index to maintain.

## Local client setup

After a fresh clone, install workspace dependencies once:

```bash
npm ci
```

The tracked client configurations start the MCP bridge directly from TypeScript, so they do **not** require committed build output:

| Client | Repository configuration |
|---|---|
| OMP | `.omp/mcp.json` |
| Claude Code | `.claude/mcp.json` |
| Cursor | `.cursor/mcp.json` |
| Gemini CLI | `.gemini/settings.json` |
| Generic MCP clients | `.mcp.json` |

Restart or reload the client after pulling configuration changes. A client that does not discover repository configuration can use the `command` and `args` from `.mcp.json`.

## Remote MCP setup

Run the HTTP process behind TLS with an API key:

```bash
CONTEXT_MCP_API_KEY='generate-a-long-random-value' NODE_ENV=production npm run start -w @market/context-server
```

Connect a remote MCP client to `https://your-host.example/mcp` and send:

```text
Authorization: Bearer <CONTEXT_MCP_API_KEY>
```

Production refuses to expose `/mcp` if `CONTEXT_MCP_API_KEY` is unset. Deploy it before configuring a hosted connector such as ChatGPT; hosted clients cannot reach `localhost`.

## MCP tools

| Tool | Args | Description |
|---|---|---|
| `get_startup_context` | — | Context card: mission, tracks, rules, phases, critical risks |
| `get_risk_register` | `severity?`, `area?` | All risks, optionally filtered |
| `get_risk` | `id` | One risk, for example `L-01` or `T-04` |
| `get_phases` / `get_phase` | `id?` | GTM phases and exit gates |
| `get_roles` / `get_role` | `squad?` / `id` | Hiring blueprint |
| `get_standing_rules` | — | Non-negotiable operating rules |
| `list_docs` / `get_doc` | `path?` | Indexed Markdown sources |
| `search_context` | `query` | Search risks, roles, phases, rules, and docs |
| `get_ai_model_assignments` | — | OMP agent-to-model map |

## Development and verification

```bash
npm run typecheck -w @market/context-server
npm run build -w @market/context-server
npm run dev -w @market/context-server
```

The dev endpoint is `http://localhost:4000/graphql`; GraphiQL is enabled outside production.

```graphql
{
  overview {
    company { name stage }
    currentPhase { name exitGate }
    criticalRisks { id threat control }
  }
  doc(path: "RISK-REGISTER.md") { title markdown }
}
```

## Update the knowledge base

Update the underlying Markdown document for narrative changes and `src/data.ts` when a structured item changes (risk, phase, role, rule, company fact, model assignment). Then run the typecheck and build. CI runs both whenever `services/context-server/**`, `docs/**`, or MCP configuration changes.
