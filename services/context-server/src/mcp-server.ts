import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { resolvers } from './resolvers.js';

const q = resolvers.Query;

/** Creates an independent MCP server so each transport owns its connection state. */
export function createContextMcpServer(): McpServer {
  const server = new McpServer({ name: 'startup-context', version: '0.1.0' });
  const text = (value: string) => ({ content: [{ type: 'text' as const, text: value }] });
  const json = (value: unknown) => text(JSON.stringify(value, null, 2));

  server.registerTool(
    'get_startup_context',
    { description: 'Full context card: mission, tracks, rules, phases, and critical risks.' },
    async () => text(q.contextCard()),
  );
  server.registerTool(
    'get_risk_register',
    {
      description: 'Risk register; filter by severity (critical|high|medium) or area (legal|technical|fraud|operational).',
      inputSchema: { severity: z.enum(['critical', 'high', 'medium']).optional(), area: z.string().optional() },
    },
    async ({ severity, area }) => json(q.risks(null, { severity, area })),
  );
  server.registerTool(
    'get_risk',
    { description: 'One risk by id, for example L-01 or T-04.', inputSchema: { id: z.string() } },
    async ({ id }) => {
      const risk = q.risk(null, { id });
      return risk ? json(risk) : text(`No risk with id "${id}". Use get_risk_register to inspect known IDs.`);
    },
  );
  server.registerTool(
    'get_phases',
    { description: 'All GTM phases with windows, goals, and exit gates.' },
    async () => json(q.phases()),
  );
  server.registerTool(
    'get_phase',
    { description: 'One phase by id (0–4).', inputSchema: { id: z.string() } },
    async ({ id }) => json(q.phase(null, { id }) ?? { error: `No phase ${id}` }),
  );
  server.registerTool(
    'get_roles',
    { description: 'Human roles blueprint; optionally filter by engineering, legal, or growth.', inputSchema: { squad: z.enum(['engineering', 'legal', 'growth']).optional() } },
    async ({ squad }) => json(q.roles(null, { squad })),
  );
  server.registerTool(
    'get_role',
    { description: 'One role by id, R1 through R20.', inputSchema: { id: z.string() } },
    async ({ id }) => json(q.role(null, { id }) ?? { error: `No role ${id}` }),
  );
  server.registerTool(
    'get_standing_rules',
    { description: 'The six non-negotiable operating rules.' },
    async () => json(q.standingRules()),
  );
  server.registerTool(
    'list_docs',
    { description: 'Every markdown document in the startup context index.' },
    async () => json(q.docs()),
  );
  server.registerTool(
    'get_doc',
    { description: 'Raw markdown by path; fuzzy paths such as PLAN.md and RISK-REGISTER.md work.', inputSchema: { path: z.string() } },
    async ({ path }) => {
      const doc = q.doc(null, { path });
      return doc ? text(`# ${doc.title}\n\n_Path: ${doc.path}_\n\n${doc.markdown}`) : text(`No document matches "${path}". Use list_docs.`);
    },
  );
  server.registerTool(
    'search_context',
    { description: 'Free-text search across risks, roles, phases, rules, and indexed docs.', inputSchema: { query: z.string().min(1) } },
    async ({ query }) => json(q.search(null, { query })),
  );
  server.registerTool(
    'get_ai_model_assignments',
    { description: 'OMP agent-to-model assignment map from docs/AISmartUsage.md.' },
    async () => json(q.aiUsage()),
  );
  return server;
}
