export const typeDefs = /* GraphQL */ `
  """
  Canonical context API for the Decentralized-Network startup.

  Every AI tool (OMP, Claude, ChatGPT, Gemini, Cursor, Copilot)
  resolves its context through this schema. Source of truth: the
  files under docs/ — SAFE-EXECUTION-PLAN.md, RISK-REGISTER.md,
  ROLES.md, PLAN.md, AISmartUsage.md.
  """
  type Query {
    """One-call overview: company, tracks, phases, rules."""
    overview: Overview!

    """Compact card for LLM system-prompt injection."""
    contextCard: String!

    """Full startup profile."""
    company: Company!

    """Risk register. Filter by prefix, e.g. risk(id: "T-04"),
       risk(ids: ["L-01", "T-01"]), or by severity. """
    risk(id: ID): Risk
    risks(severity: Severity, area: String): [Risk!]!

    """Standing rules (SEP section 9)."""
    standingRules: [StandingRule!]!
    standingRule(id: Int!): StandingRule

    """Engineering & business roles (see docs/ROLES.md)."""
    roles(squad: String): [Role!]!
    role(id: ID!): Role

    """Go-to-market / build phases."""
    phases: [Phase!]!
    phase(id: ID!): Phase

    """Fetch the raw text of a context document by path, e.g.
       doc(path: "docs/PLAN.md") or "SAFE-EXECUTION-PLAN.md". """
    doc(path: String!): Document

    """List every doc this server can serve."""
    docs: [DocMeta!]!

    """Free-text search across the loaded knowledge base."""
    search(query: String!): [SearchHit!]!

    """LLM model assignments + OMP wiring (AISmartUsage)."""
    aiUsage: AiUsage!
  }

  # ---------- Entities ----------

  type Overview {
    company: Company!
    tracks: [Track!]!
    currentPhase: Phase!
    standingRules: [StandingRule!]!
    riskCount: Int!
    criticalRisks: [Risk!]!
  }

  type Company {
    name: String!
    tagline: String!
    mission: String!
    repository: String!
    hq: String!
    founded: String!
    stage: String!
  }

  type Track {
    id: ID!
    name: String!
    status: String!
    description: String!
    wedge: String!
  }

  enum Severity { critical high medium }

  type Risk {
    id: ID!
    severity: String!
    area: String!
    threat: String!
    control: String!
  }

  type StandingRule {
    id: Int!
    rule: String!
  }

  type Role {
    id: ID!
    title: String!
    squad: Squad!
    focuses: String!
  }

  enum Squad { engineering legal growth }

  type Phase {
    id: ID!
    name: String!
    status: String!
    window: String!
    goals: String!
    exitGate: String!
  }

  type DocMeta {
    path: String!
    title: String!
    bytes: Int!
    updated: String
  }

  type Document {
    path: String!
    title: String!
    markdown: String!
  }

  type SearchHit {
    kind: HitKind!
    ref: String!     # doc path, risk id, role id, or clause ref
    snippet: String!
    score: Float!
  }

  enum HitKind { doc risk role phase rule }

  type AiUsage {
    subscriptions: [String!]!
    modelFor(role: String!): String
    assignments: [ModelAssignment!]!
    costPerMonthUsd: Int!
  }

  type ModelAssignment {
    ompAgent: String!
    model: String!
  }
`;
