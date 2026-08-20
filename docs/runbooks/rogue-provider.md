# Runbook: rogue or impersonated provider

**Severity:** SEV-0 if customer work/credentials were issued; otherwise SEV-1

**Trigger:** unauthorized enrollment, impossible attestation, duplicate device
identity, anomalous claims/results, stolen node token, or provider abuse report.

1. Disable/quarantine the enrollment and all linked node aliases centrally;
   revoke node credentials and outstanding leases/transfer capabilities.
2. Prevent payout/billing finalization for affected evidence without modifying
   raw audit records. Do not accuse the provider publicly.
3. Bound jobs/content/capabilities issued, enrollment/auth events, image/agent
   digests, result anomalies and linked keyed-HMAC device records.
4. If work was issued to an unauthorized node, invoke
   `suspected-data-exposure.md` and notify counsel.
5. Identify the entry path: open registration, stolen plaintext token,
   re-registration takeover, compromised platform credential, or attestation
   validation flaw. Disable the path fleet-wide.
6. Require verified re-enrollment, fresh hardware-backed identity and current
   audit before restoring a legitimate provider. Preserve the internal stable
   identity for abuse history; rotate public aliases.
