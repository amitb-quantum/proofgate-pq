# Wire protocol v1

All signed application objects use PGJ-1. Transport input is at most 1,048,576 bytes;
decoded nesting is at most 32; integers are within +/- (2^53 - 1). Strings contain only
U+0020 through U+007E. Object keys are unique strings; keys sort by ASCII value. Arrays
preserve order. Serialization uses JSON string escaping, decimal integers, `true`, `false`
and `null`, no insignificant spaces, no trailing newline. The file writer may add a
transport newline; that newline is not signed. JSON duplicate aliases such as `a` and
`\u0061` collide after decoding and are rejected. Number `-0` is rejected on input.

For domain D and value V:

```text
digest = hex(SHA384(ASCII("ProofGate-PQ/v1/" + D) || 0x00 || PGJ1(V)))
signed_message = ASCII("ProofGate-PQ/v1/" + role) || 0x00 ||
                 PGJ1({"suite": suite, "signer": identity, "body": object})
```

Roles are `intent`, `attestation`, `result`; `benchmark` is separate and never accepted
as an authorization signature. Digest domains include `intent`, `experiment`, `policy`,
`receipt` and `replay`. Domain labels are code constants, not caller-selected wire fields.
Use ordinary provider signing, not raw/internal ML-DSA functions or invented prehash modes.

Signatures are maps from exact algorithm labels to canonical padded RFC 4648 base64.
Public trust maps use the same encoding of raw public-key bytes. Private demo key maps
contain provider-exported raw seed bytes. For hybrid, both algorithms sign the same bytes;
both signatures must verify using their independently pinned component keys.

## Evidence envelope

`SignedIntent = {intent, signatures}`. The intent signature proves requester identity,
not authorization. `Receipt = {header, disposition, attestations}`. Each attestation is
`{body: {header, verifier_id, disposition, predicates}, signatures}`.

Header identity and all constraints are checked against the request and current trusted
policy. Every included attestation's header must equal the outer header. All included
signatures must verify; identities must be distinct, known and eligible. Every attestation's
predicates and disposition must equal deterministic reevaluation. ALLOW needs the pinned
threshold. Outer disposition is derived from evidence: threshold ALLOW, otherwise DENY,
HUMAN_VERIFY, ERROR or UNKNOWN in that precedence. Empty evidence yields UNKNOWN.

This supports verifiable negative evidence, but cannot establish the absence of omitted
votes or global consensus. Attestation order is not authorization-relevant. A valid subset
can still authorize if it meets quorum. Changing an included signed field invalidates the
signature; merely reserializing or reordering objects does not. A result's receipt digest
binds the exact canonical receipt including list order and signature bytes used at execution.

## Freshness and use

Trusted time checks enforce intent creation <= receipt issuance <= now < receipt expiration
<= intent expiration, plus local TTL maxima. Schema timestamps are integer Unix seconds UTC.
There is no permissive clock-skew allowance. The executor always obtains real wall-clock
time; the standalone verifier takes trusted caller time to permit deterministic testing and
historical provenance verification. Historical result verification cannot execute actions.

Replay identity is SHA-384 over the domain-separated object containing audience, subject
and intent nonce. Receipt and replay identities are unique in one SQLite reservation table.
Reservation commits before side effects; result persistence is a subsequent operation.
After a failure the caller must reconcile manually, not erase replay state and retry.

## Versioning

Schema v1 and `builtin-statevector-v1` define fixed interpretation. Never change their
semantics without new version identifiers and review. The policy content digest binds
limits, identity list, threshold, suite, audience and context. Policy history/trust bundles
are administratively supplied, not selected by a receipt. New algorithms require a new
suite registry entry, provider implementation and tests; unknown suites never fall back.

The generated schemas are structural specifications. PGJ-1 canonical rules, exact integer
literal typing, cross-field timing, distinct-key ownership, cryptographic validity, quorum
and policy semantics require the runtime checks as well.
