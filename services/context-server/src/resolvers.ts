import { readFileSync, readdirSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, relative } from 'node:path';
import {
  COMPANY, TRACKS, PHASES, STANDING_RULES,
  MODEL_ASSIGNMENTS, RISKS, ROLES,
} from './data.js';

// Repo root = two levels above services/context-server/
const REPO_ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..', '..');

// ---------- Doc catalog: index every markdown file under docs/ ----------

function listDocs(dir: string, out: Array<Record<string, unknown>> = []): Array<Record<string, unknown>> {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) {
      listDocs(full, out);
    } else if (entry.endsWith('.md')) {
      const text = readFileSync(full, 'utf-8');
      const lines = text.split('\n');
      const title = lines.find((l) => l.startsWith('# '))?.replace(/^#\s*/, '') ?? entry;
      out.push({
        path: relative(REPO_ROOT, full).replaceAll('\\', '/'),
        abs: full,
        title,
        bytes: st.size,
        updated: st.mtime.toISOString(),
        markdown: text,
      });
    }
  }
  return out;
}

const DOC_INDEX = listDocs(join(REPO_ROOT, 'docs'));
// Root-level strategy docs live outside docs/ — register them too
for (const extra of ['README.md']) {
  const full = join(REPO_ROOT, extra);
  try {
    const st = statSync(full);
    DOC_INDEX.push({
      path: extra, abs: full,
      title: readFileSync(full, 'utf-8').split('\n')[0].replace(/^#\s*/, ''),
      bytes: st.size, updated: st.mtime.toISOString(),
      markdown: readFileSync(full, 'utf-8'),
    });
  } catch { /* file may not exist in production image */ }
}

function findDoc(pathQuery: string) {
  const q = pathQuery.toLowerCase();
  return DOC_INDEX.find((d) =>
    (d.path as string).toLowerCase() === q ||
    (d.path as string).toLowerCase().endsWith('/' + q) ||
    (d.path as string).toLowerCase().includes(q),
  );
}

// ---------- Search ----------

function searchAll(query: string) {
  const q = query.toLowerCase();
  const hits: Array<Record<string, unknown>> = [];
  const snippet = (text: string, needle: string): string => {
    const i = text.toLowerCase().indexOf(needle);
    if (i === -1) return text.slice(0, 180);
    return text.slice(Math.max(0, i - 60), i + 120).replace(/\s+/g, ' ').trim();
  };

  for (const d of DOC_INDEX) {
    if ((d.markdown as string).toLowerCase().includes(q)) {
      hits.push({ kind: 'doc', ref: d.path, snippet: snippet(d.markdown as string, q), score: 1.0 });
    }
  }
  for (const r of RISKS) {
    if (`${r.threat} ${r.control} ${r.area}`.toLowerCase().includes(q)) {
      hits.push({ kind: 'risk', ref: r.id, snippet: `${r.threat} → ${r.control}`, score: 1.2 });
    }
  }
  for (const r of ROLES) {
    if (`${r.title} ${r.focuses}`.toLowerCase().includes(q)) {
      hits.push({ kind: 'role', ref: r.id, snippet: `${r.title}: ${r.focuses}`, score: 1.0 });
    }
  }
  for (const p of PHASES) {
    if (`${p.name} ${p.goals}`.toLowerCase().includes(q)) {
      hits.push({ kind: 'phase', ref: p.id, snippet: `${p.name} — ${p.goals.slice(0, 120)}`, score: 1.0 });
    }
  }
  for (const r of STANDING_RULES) {
    if (r.rule.toLowerCase().includes(q)) {
      hits.push({ kind: 'rule', ref: `Rule ${r.id}`, snippet: r.rule, score: 1.1 });
    }
  }
  return hits.sort((a, b) => (b.score as number) - (a.score as number)).slice(0, 12);
}

// ---------- Resolvers ----------

function buildContextCard(): string {
  const crit = RISKS.filter((r) => r.severity === 'critical');
  return [
    `# ${COMPANY.name} — Startup Context Card`,
    ``,
    `**Mission:** ${COMPANY.mission}`,
    `**Stage:** ${COMPANY.stage} | **HQ:** ${COMPANY.hq}`,
    `**Repo:** ${COMPANY.repository}`,
    ``,
    `## Dual Tracks`,
    ...TRACKS.map((t) => `- **${t.name}** (${t.status}): ${t.wedge}`),
    ``,
    `## Standing Rules`,
    ...STANDING_RULES.map((r) => `${r.id}. ${r.rule}`),
    ``,
    `## Tech Stack`,
    `TS strict ESM · npm workspaces · React+Vite+Tailwind · Zod contracts ·`,
    `PostgreSQL · gVisor sandbox (target) · WebRTC streaming (Phase 2)`,
    ``,
    `## Phases`,
    ...PHASES.map((p) => `- P${p.id} (${p.status}) ${p.name} [${p.window}] — exit: ${p.exitGate}`),
    ``,
    `## Critical Risks (${crit.length} of ${RISKS.length} total)`,
    ...crit.map((r) => `- ${r.id}: ${r.threat}`),
  ].join('\n');
}

export const resolvers = {
  Query: {
    overview: () => ({
      company: COMPANY,
      tracks: TRACKS,
      currentPhase: PHASES.find((p) => p.status === 'in-progress') ?? PHASES[1],
      standingRules: STANDING_RULES,
      riskCount: RISKS.length,
      criticalRisks: RISKS.filter((r) => r.severity === 'critical'),
    }),
    contextCard: () => buildContextCard(),
    company: () => COMPANY,

    risk: (_: unknown, { id }: { id: string }) => RISKS.find((r) => r.id === id) ?? null,
    risks: (_: unknown, { severity, area }: { severity?: string; area?: string }) =>
      RISKS.filter((r) =>
        (!severity || r.severity === severity) &&
        (!area || r.area === area),
      ),

    standingRules: () => STANDING_RULES,
    standingRule: (_: unknown, { id }: { id: number }) => STANDING_RULES.find((r) => r.id === id) ?? null,

    roles: (_: unknown, { squad }: { squad?: string }) =>
      squad ? ROLES.filter((r) => r.squad === squad) : ROLES,
    role: (_: unknown, { id }: { id: string }) => ROLES.find((r) => r.id === id) ?? null,

    phases: () => PHASES,
    phase: (_: unknown, { id }: { id: string }) => PHASES.find((p) => p.id === id) ?? null,

    doc: (_: unknown, { path: p }: { path: string }) => {
      const found = findDoc(p);
      return found ? { path: found.path, title: found.title, markdown: found.markdown } : null;
    },
    docs: () => DOC_INDEX.map((d) => ({ path: d.path, title: d.title, bytes: d.bytes, updated: d.updated })),

    search: (_: unknown, { query }: { query: string }) => searchAll(query),

    aiUsage: () => ({
      subscriptions: ['ChatGPT Plus ($20/mo)', 'Claude Pro ($20/mo)'],
      assignments: Object.entries(MODEL_ASSIGNMENTS).map(([ompAgent, model]) => ({ ompAgent, model })),
      costPerMonthUsd: 40,
    }),
  },
  AiUsage: {
    modelFor: (parent: { assignments: Array<{ ompAgent: string; model: string }> }, { role }: { role: string }) =>
      parent.assignments.find((a) => a.ompAgent === role)?.model ?? null,
  },
};
