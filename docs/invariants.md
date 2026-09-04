# Invariant-to-evidence map

These are implementation requirements and finite regression evidence, not formal proofs.
The trusted boundary and failure assumptions are in architecture.md.

| Invariant | Mechanism | Automated evidence |
|---|---|---|
| No receipt, no action | Executor calls public receipt verifier before store/adapter | `test_no_receipt_no_effect` |
| Exact canonical intent binding | Request signature plus signed SHA-384 intent digest | Corpus payload/target/spec cases; every intent leaf; generated mutations |
| Policy version/content binding | Reference and content digest checked against local policy | Incorrect policy version and same-version changed-content corpus cases |
| Suite binding and no downgrade | Exact pinned suite and component maps at all roles | Both suite downgrade cases, unknown suite, missing/extra components |
| Only currently valid receipt | Intent/header bounds, real-clock reservation and post-reservation check | Expired/future cases; expiration during reservation |
| No receipt/intent replay | SQLite transaction with unique receipt and intent identities | Replay, reissuance, restart, six-process race |
| Adequate authenticated quorum | All included signatures validate; threshold pinned | Insufficient quorum, 3-of-3 missing member, two honest members |
| No duplicate independent identities | Unique IDs and non-reused component keys | Duplicate/unknown verifier, shared-key and repeated-identity property |
| Bound-field mutation rejected | Domain-separated signatures and constraint checks | Exhaustive attestation leaves, evidence/header changes, PQ bit mutation |
| Ambiguity/errors fail closed | Strict parse and explicit disposition checks | Canonical malformed corpus, absent evidence, DENY/HUMAN/UNKNOWN/ERROR |
| Role substitution rejected | Distinct message domains and signer binding | Signature substitution and cross-domain corpus cases |
| Executor/context confinement | Bound audience, target, project, environment | Audience/target mutations and generated intent leaf checks |
| Immutable execution snapshot | Strict parsing into newly owned models from bytes | Caller mutation during reservation test |
| Tamper-evident provenance | Executor signs result and request/spec/receipt digest bindings | Result tampering, quantum demo, historical result verification |
| No hidden primitive fallback | Provider errors become structured rejection | Unavailable-provider and unknown-suite tests |
| Storage/execution failure is not approval | Fail before effect; spent reservation retained after adapter error | Store failure and failed-adapter tests |

Quorum ordering and removal of surplus valid votes intentionally do not alter the exact
authorized action. They are valid evidence-selection operations, not mutations to signed
action semantics. Result provenance separately hashes the complete receipt used at execution.
