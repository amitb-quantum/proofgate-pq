# Limits, assumptions, and unsupported claims

## Demonstrated

The automated corpus exercises authorization/rejection under three actual signature
suites. The quantum demo runs three OS processes with distinct signing keys and verifies
their attestations locally. Tests exercise durable replay across new executor instances,
six concurrent CLI processes, malformed inputs, hybrid signature removal, signed false
predicate evidence, policy changes and mutable-input snapshot protection.

These finite executions are evidence for tested behavior, not a formal security proof.
Machine-readable tests and benchmark samples are in reports/. CI configuration is supplied;
the original Windows baseline and current WSL/GPU runs are substantiated. Remote CI was not triggered.

## Deliberate scope

- No SLH-DSA adapter or ML-KEM/key-establishment protocol. Both were researched; neither
  is silently replaced by another algorithm. No SLH-DSA benchmark numbers exist here.
- Three distinct identities/processes share code, host, policy, filesystem owner and input.
  There is no claim of organizational independence, diverse policy implementations,
  malicious-host tolerance, remote attestation or Byzantine consensus.
- Every verifier recomputes the same explicit deterministic predicates. Predicates do
  not authenticate external scientific observations or establish that an experiment
  is meaningful. The policy and frozen specification are the evidence sources.
- The adapter performs bounded real-valued statevector simulation for H/X/Z/CX only.
  It does not support arbitrary complex gates, noise, calibration, or hardware execution.
  A new backend revision, gate language or parameter needs a new reviewed schema/policy.
- A signed result proves what the trusted executor key attested. It cannot prove the
  computation happened correctly or when it happened. Historical verification uses the
  signed execution timestamp and retained trust snapshot, not a trusted timestamp service.
- SQLite reservation is at-most-once admission. Failures after reservation burn permits.
  Crashes can lose results. There is no exactly-once guarantee across a future remote API.
- Replay is lost if the administrator deletes/rolls back the database, changes its path,
  or runs the same audience against independent databases. Distributed storage and
  backend idempotency are deployment requirements, not solved by a signature.
- Plaintext demo keys are unsuitable for security deployment. No HSM/KMS, secret zeroization,
  certificate infrastructure, dynamic revocation or migration rollout protocol is implemented.
- One active pinned policy is supported. Old receipts fail under changed contents even
  with the same version number. Archive the original trust bundle for historical audit.
- The coordinator requests all three local processes and fails on a process error/timeout.
  A caller may explicitly assemble a valid subset meeting the threshold. There is no
  automatic Byzantine filtering, retry, deny-veto rule or availability SLA.
- PGJ-1 intentionally rejects Unicode, floating point and unknown fields. Generated JSON
  schemas describe object structure; canonical-profile rules and cross-field constraints
  are enforced by the parser and protocol, beyond what the schemas alone establish.
- Benchmarks use small samples and include Python/key-import overhead. They are local
  comparative observations, not primitive speed claims, capacity planning or latency SLAs.

## Review discoveries

Initial execution testing found a SQLite connection lifetime bug: Python's connection
context manager commits/rolls back but does not close the handle. The corrected code uses
explicit closing; the Windows attack corpus now cleans up and the process race passes.
Threat review also identified Python `True == 1` accepting a schema-version literal;
the model base now requires the exact integer type before schema validation.

The initial test harness needed compact parameter IDs for an oversized Windows input
and explicit Hypothesis fixture reuse settings. These were harness fixes, not bypasses:
each generated test mutates a fresh document copy; large input rejection remains tested.

## Not substantiated

No production readiness, independent security audit, FIPS module validation, cross-provider
interoperability/conformance testing, resistance to side channels, formal composition proof,
honest execution on a compromised host, paid hardware quantum run,
or deployed CI result is claimed. The primitive implementation is supplied by PyCA/OpenSSL;
the protocol and its tests do not replace provider conformance or external review.

## WSL GPU and adversarial continuation

See gpu-results.md and redteam-analysis.md for the version-2 Aer CPU/GPU extension,
measured crossover, actual rollback/false-provenance reproductions and narrower claims.
The real-valued built-in simulator limitation above applies to v1; Aer v2 also supports
complex T gates and up to 26 qubits. A policy-file edit is not automatic live revocation.
