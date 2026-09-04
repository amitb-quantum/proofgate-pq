# Security scope

ProofGate-PQ is an unaudited research prototype. Do not use it to protect production
funds, equipment, credentials, infrastructure or safety-critical experiments.

The protected entry point is `ProtectedExecutor.execute`. A receipt is a short-lived
bearer capability for one exact action at one executor audience. Possession does not
authorize any different action. The CLI is a local administration/demo tool: whoever
controls its trust file, private keys, code or database controls the security boundary.

Provisioned private key JSON is plaintext and ignored by Git. POSIX demo provisioning
uses directory mode 0700 and file mode 0600. Windows inherits directory ACLs; it does
not establish separate OS accounts or harden ACLs. A single user can read all demo
keys. Never treat these co-located keys as independent administrative security domains.

To review a possible issue, preserve the minimal non-secret input, expected invariant,
observed rejection/result and environment. No external disclosure destination has
been configured for this unpublished repository; do not attach private keys or secrets.

Production work requires independent protocol/security review, cryptographic provider
conformance assessment, key custody and rotation, trust distribution, authenticated
transport, backend credential isolation, robust time, rollback-resistant replay state,
resource isolation, audit retention, fuzzing and operational incident procedures.
See docs/architecture.md and docs/limitations.md for precise assumptions.
