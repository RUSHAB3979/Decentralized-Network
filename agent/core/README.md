# `agent/core/` — the hand-built half

Everything in this package is written by hand, by the founder, per
[ADR 0002](../../docs/adr/0002-generated-vs-handbuilt.md). The rest of the
provider app — the tray, the Ollama supervisor, the packaging — is generated.

The line is not "backend versus frontend" and not "hard versus easy". It is
**does it raise when it is wrong?** Everything in this package answers no:

| Module | What it does | How it fails silently |
|---|---|---|
| `creds.py` | Machine identity and the orchestrator credential | A credential stored somewhere readable still works perfectly. Nothing raises. The provider's machine is simply now a way into the marketplace for anyone with local access |
| `lease.py` | Claim a job, hold it, drain, hand it back | A lease that is not released on crash still expires eventually. In the meantime the scheduler believes a GPU is busy that is idle, and the only symptom is revenue being lower than it should be |
| `meter.py` | Count what is owed | Undercounting is invisible from the inside. Every request succeeds, every customer is happy, and the provider is paid too little. Overcounting is worse and equally quiet |

Each module currently defines its interface and raises `NotImplementedError`.
The app runs without them: v1 supervises Ollama and shows status, and does not
connect to the orchestrator yet. Nothing here is on the critical path until
that connection exists, which is deliberate — it means these can be written
slowly and carefully rather than under pressure to make the app boot.

Two constraints from elsewhere in the repo that bind this package:

- **A customer token must never reach a provider machine.** It terminates at
  the gateway. If a design here needs one, the design is wrong.
- **`agent/requirements.txt` is a security boundary.** No database driver,
  ever. This code talks to the orchestrator over HTTP and to Ollama over
  localhost, and to nothing else.
