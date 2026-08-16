# ADR 0005 — Provider accounts, and how a machine enrols into one

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-16 |
| **Owner** | [@RUSHAB3979](https://github.com/RUSHAB3979) (R1 Architect) |
| **Implemented by** | [@YogitaKanwar](https://github.com/YogitaKanwar) — `docs/yogitatasks.md` Y6–Y11 |
| **Supersedes** | [ADR 0004](0004-m1-unauthenticated-heartbeat.md), on the condition stated below |

## Context

A provider today is not an account. It is a row in `provider_nodes` keyed by a `node_id` that
the agent derives from the machine's Windows MachineGuid. There is no person attached to it,
no way for a human to log in and look at their own hardware, and no way to say that one
machine belongs to one provider and a second belongs to somebody else.

That was a deliberate M1 position and it has run out of road. Three things have changed:

**1. Registration is unauthenticated and mints a credential.**
`POST /providers/register` (`orchestrator/main.py:180`) accepts any caller, upserts a row, and
returns a freshly minted `node_token` (`:247`) that is required by `/providers/work/claim` and
by the result endpoint. Anyone who can reach the endpoint and guess or observe a `node_id` is
issued a working credential for it.

This is precisely the enrolment shape `agent/core/creds.py` examines and rejects in its design
question 1:

> *(b) Trust on first registration. The first `POST /providers/register` for an unseen node_id
> returns a secret. Zero friction, and wrong: a node_id is derivable from a machine the
> attacker does not have to own, and the first caller wins. Only acceptable if registration is
> itself gated.*

Registration is not gated. We shipped the option that module told us not to ship.

**2. ADR 0004 has expired by its own terms.** It named four conditions, any one of which ends
the exception, and listed first: *"a lease can be claimed by node id (M2)"*. PR #43 shipped
exactly that. It also imposed a deployment constraint — *"While this ADR stands, the
orchestrator must not be exposed to the public internet"* — and the orchestrator has been on
Render since PR #44. Both halves of that ADR are now false in practice.

**3. Nothing can be paid to anybody.** Earnings require knowing whose machine did the work.
`provider_nodes` has no owner column, so there is no answer to that question at all.

## Decision

### 1. Provider accounts are fully separate from customer accounts

New `provider_accounts` and `provider_sessions` tables, independent of `users` and
`user_sessions`. A human who both buys inference and sells GPU time signs up twice and holds
two logins.

The considered alternative was one `users` table with a provider capability flag, which avoids
duplicating an auth stack. That was rejected in favour of a clean separation between the two
sides of the marketplace: the surfaces, the data each side may read, and eventually the KYC and
payout obligations attached to a seller are different enough that entangling them in one row is
the harder thing to unpick later.

**The cost is stated plainly, because it is the whole cost of this decision:** a second account
system is a second chance to get password storage, session expiry and revocation wrong. That is
mitigated by a rule, not by hope — see *Consequences*.

### 2. Enrolment is by a key generated in the console

The provider signs in, generates an enrolment key, and pastes it into the desktop app. The
agent trades that key for a long-lived node credential, and the resulting node row is bound to
the account that minted the key.

This is option (a) from `creds.py` design question 1, chosen for the reason that module already
gives: it *"binds the node to a human account, which is what payouts will eventually require."*
The friction it costs — a UI flow the app does not have — is the subject of task Y10.

The key is short-lived, single-use, revocable, and stored only as a digest. The plaintext is
returned exactly once at creation, matching the existing pattern for customer API keys
(`create_api_key`, `orchestrator/main.py:425`).

### 3. The hand-built boundary is split, not moved

`agent/core/creds.py` — storing the credential on the provider's machine, rotating it, caching
it, and refusing to downgrade when it cannot be read — remains hand-built under ADR 0002 and
remains R1's to write. Its own docstring explains why: *"a credential stored badly works
exactly as well as one stored well. There is no test that goes red, no traceback, and no moment
where the provider finds out."*

Everything on the other side of that line is generated work and is assigned: the account
tables, the auth endpoints, the enrolment-key endpoints, the console, and the desktop screen
that collects the key and calls `creds.store()`.

The seam is a function call. Y10 calls `store()`; it does not implement it.

### 4. The console shows earnings, labelled as unbacked

The provider console gets a full set of surfaces including earnings and payout, even though
`agent/core/meter.py` still raises `NotImplementedError` and no usage is metered.

Every figure that is not backed by a real measurement must carry a visible marker saying so.
The existing `ProviderConsolePage.jsx` already does this — per-card `Live` / `Preview` badges
and an explicit header disclaimer — and that pattern is a requirement of the work, not a
stylistic preference. A dashboard that mixes measured and invented numbers without marking
which is which is how a placeholder becomes a number somebody quotes in a pitch.

## What this changes about ADR 0004

ADR 0004 is superseded **when Y8 lands**, not when this document is merged. The specific change
that retires it is `/providers/register` refusing to mint a credential for a node that has not
presented a valid enrolment key.

Until then, the gap ADR 0004 describes is not merely still open — it is open under conditions
that ADR explicitly said it did not cover, because the orchestrator is now public. Rate
limiting, which ADR 0004 called *"the obvious next mitigation […] worth doing before the
endpoint is exposed outside localhost"*, is still not in place and is still worth doing
independently of this work.

## Consequences

**One password implementation, not two.** `orchestrator/auth.py` already provides
`hash_password`, `verify_password`, `normalise_email`, `issue_session_token`, `hash_token`,
`session_expiry` and `session_is_valid`, with the scrypt-over-SHA256 reasoning written out at
length. Provider auth reuses those functions unchanged. A separate account *table* is what was
decided; a separate *hasher* was not, and a second one appearing is the failure this ADR most
expects and the first thing to look for in review.

**Existing nodes have no owner and must keep working.** `provider_nodes` has live rows today.
`provider_account_id` is added nullable, exactly as `marketplace_api_keys.user_id` was when
accounts arrived, so unowned nodes keep heartbeating until somebody claims them. How they get
claimed is an open question for Y6 to answer rather than quietly decide.

**A restore-from-backup must not brick the fleet.** `creds.py` design question 3 is binding
here: a machine holding a valid credential but having no row in the registry must still be able
to re-register. Today that self-heals through the 404 path in `agent/reporter.py`. If gating
registration closes that path, a database restore silently disables every provider at once and
they will not all reinstall.

**A credential must be bound to the node it claims to be.** `creds.py` design question 2: if
the credential is verified but never matched against the `node_id` in the request body, any
enrolled node can act as any other and the check has bought nothing.

**Migration pressure increases.** This adds three tables and one column to a schema with no
migration tool — `orchestrator/schema.sql` is still applied by idempotent DDL. All four changes
are reachable that way, so this does not breach the ceiling that file describes at line 151,
but it moves closer to it. Y4 remains unstarted and remains the right answer.

## Expiry condition

This ADR stands until provider payouts exist. The moment money is computed from a node's
recorded work, the questions this document leaves open — how an account is verified, what
happens to earnings on a disputed node, how a machine is transferred between accounts — stop
being design questions and become financial ones, and they need their own decision record.
