# Runbook: credential or secret leak

**Severity:** SEV-0 for production/KMS/storage/signing/admin credentials; SEV-1
for scoped node/session credentials with no observed use.

1. Identify secret *type and scope without printing its value*. Revoke/rotate
   it at the authority first; disabling a Git commit does not revoke a secret.
2. Disable affected automation/nodes and invalidate sessions, presigned
   capabilities or signing trust as appropriate.
3. Search authority/access logs for use from issuance through revocation using
   key ID/fingerprint and UTC, not the secret. Invoke data-exposure response on
   unauthorized access.
4. Replace the secret in deployment stores and restart only dependent services.
   Verify the old value fails and the new one works.
5. Remove the value from current files and, with explicit founder approval,
   rewrite git history/cache/forks where justified. History rewriting is
   disruptive and never substitutes for rotation.
6. Add a redacted regression rule/test that detects the secret pattern or exact
   fingerprint without exposing it. Review logs/artifacts from scanners.

The repository contains a known historical database credential finding not
detected by the current gitleaks rule set. Its value must never be copied into a
ticket or runbook. Rotation is urgent; history purge remains founder-approved
work because it rewrites shared commits.
