# Architecture and threat model

Design baseline written before implementation, 2026-09-04.

## Boundary

Signed intent -> three verifier processes -> evidence receipt -> independent receipt
validation inside protected executor -> durable replay reservation -> simulator -> signed result.

The requester and coordinator are untrusted for authorization. Verifiers independently
validate requester signatures, the pinned policy, the frozen experiment hash, resource
limits, context and supported circuit semantics. The executor repeats these deterministic
checks and verifies every included attestation against locally pinned public keys. A
coordinator signature is neither necessary nor sufficient. No coordinator secret exists.

Only the executor has the result-signing key and replay database in the intended deployment.
Python object privacy is not an OS security boundary: a process owner can run their own
simulator or replace code. The guarantee applies to the protected executor entry point
and requires exclusive control of a real backend's credentials by that service.

## Invariants

1. The executor's only action entry point requires a valid ALLOW receipt.
2. Request and attestations bind the exact canonical intent, including the frozen spec.
3. Policy identifier, version AND content digest must match locally pinned policy.
4. Suite identifiers and exact required signature components are bound and locally pinned.
5. Validity is `created <= issued <= now < expires <= intent.expires`, with bounded TTL.
6. Receipt IDs and `(executor, subject, intent nonce)` are atomically reserved before
   side effects. Reissuance of the same intent cannot evade replay protection.
7. Missing providers/signatures and suite negotiation/downgrade fail closed.
8. Only distinct, authenticated, eligible ALLOW signers with expected predicate evidence
   count toward quorum. Policy recomputation must also return ALLOW.
9. Duplicate identities, duplicate component keys across identities, unknown signers,
   malformed attestations and inconsistent evidence are rejected.
10. Security-relevant field mutations invalidate signatures or pinned constraints.
11. DENY, HUMAN_VERIFY, UNKNOWN, ERROR, missing evidence and malformed inputs cannot execute.
12. Request, verifier and result signatures have distinct domain-separated messages.
13. Executor audience, simulator revision, environment, project and requester are bound.
14. Parse strictly; reject duplicate JSON keys, floats, non-ASCII strings, unknown fields,
    oversize documents, excessive depth, invalid types and unsupported schema versions.
15. Execute a fresh parsed snapshot of the verified spec, not caller-owned mutable data.
16. Result signatures bind counts, action/spec/receipt digests, executor and execution time.

## Protocol choices

PGJ-1 is a deliberately narrow canonical JSON profile, not a claim of RFC 8785 compliance.
It permits printable ASCII strings, JSON booleans/null, bounded integers, arrays and
objects with sorted ASCII keys. No floats, Unicode normalization or numeric coercion.
Compact JSON with no whitespace is ASCII-encoded; integers use decimal notation.
Noncanonical transport whitespace/key order is accepted and canonicalized; duplicate
keys and ambiguous numeric encodings are rejected. SHA-384 hashes domain-separated
canonical bytes. Structured schemas reject unrecognized fields.

A receipt contains a common header (intent/policy digests, suite, eligible verifier set,
threshold, audience, issuance/expiration, unique receipt ID) and signed attestation bodies.
Each body includes that whole header, identity, disposition and explicit predicates.
The outer disposition is recomputed. It is a derived summary, not coordinator authority.
The included attestation list is evidence; removing surplus valid ALLOW evidence may
leave a valid quorum. This is intentional subset semantics, not immutable envelope bytes.
Every included attestation must validate; a malformed surplus signature fails closed.
An omitted verifier cannot veto: this is threshold approval, not unanimous deny-veto.

The active trust bundle pins a single policy version and suite. A replacement bundle
invalidates old receipts if policy contents/keys change; history must be retained by an
external archive for audit. No receipt-controlled policy lookup or fallback exists.

## Threats and assumptions

Attackers may control the requester/coordinator, mutate or substitute all transport bytes,
replay concurrently, and compromise fewer than the threshold verifier identities.
With k honest-checking approvals required, a quorum establishes signed agreement about
the stated deterministic predicates, not scientific truth or independent physical evidence.
Three local processes have distinct keys and PIDs but share implementation, host, policy
and input. They are NOT independent administrative fault domains or Byzantine consensus.

Trust anchors, runtime, OS, provider, clock, replay storage and executor key must be protected.
No claims cover host compromise, a malicious policy administrator, common implementation
bugs, side channels, denial of service, key theft, clock rollback, or database rollback.
The local IPC demo provides signed integrity/authentication, not confidentiality or a
hardened remotely reachable service. No paid provider or external publishing is used.

SQLite commits a reservation before simulation. Crashes after reservation burn the permit;
this provides at-most-once admission, NOT guaranteed execution or exactly-once distributed
effects. SQLite must be durable, shared by all instances of the same executor audience,
on supported local storage, and never restored/reset while permits remain usable. Production
requires protected storage, backup/rollback defense and backend idempotency/reconciliation.

## Quantum scope

The frozen specification includes backend revision, qubits, ordered gates, shots and seed.
The built-in bounded statevector adapter supports H/X/Z/CX and computational-basis sampling.
No hardware validation or quantum advantage claim is made. The signed result attests what
the executor reports; it is not a proof of correct computation or a hardware attestation.

See research.md for standards versus application engineering choices. All invariants are
design requirements exercised by tests, not formal proofs or independent security review.
