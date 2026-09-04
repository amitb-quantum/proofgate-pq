# Red-team outcome and claim boundaries

Baseline commit: 702d66bcbfd65fa0bb584b5a882eadf613cb7a2c.
The baseline passed 179 WSL tests and type checking. It included the versioned Aer
integration and unfinished benchmark harness; one benchmark formatting warning remained.
The baseline was committed before red-team changes. This is a local adversarial review,
not an independent audit, formal verification or a proof of security.

## Concrete outcomes

See reports/redteam.json and its generated matrix for 18 reproducible hypotheses:
11 CONFIRMED FAIL-CLOSED, 2 DESIGN LIMITATION, 4 ASSUMPTION VIOLATION and
1 NOT REPRODUCED. No CONFIRMED EXPLOITABLE authorization bypass was demonstrated
within the documented trusted-runtime, trusted-policy and protected-store assumptions.

New probes included all three authenticated signers lying about a denied action,
combining valid votes from different receipt issuances, a requester re-signing a
correlated modified specification while reusing its old receipt, cross-role reuse of
only the PQ key component, Unicode-escaped duplicate security fields, truthy numeric
predicate injection, dynamic simulator operator injection and invalid surplus evidence.
Additional tests exercise simultaneous *distinct receipts* for one intent nonce,
GPU-to-CPU substitution, a fake provider claiming CPU fallback, unavailable GPUs,
legacy-schema confusion and historical v1 receipt/result compatibility.

The signed stress run issued and checked 2000 fresh hybrid authorization scenarios in
five batches. Half were valid; half re-signed correlated experiment/context mutations
against the original receipt. Every expected acceptance/rejection matched. These are
CPU operations; GPU numeric prefilter throughput is not signature or gateway throughput.

## Confirmed defects and fixes

No cryptographic, quorum or replay acceptance defect was confirmed in this pass, so
no speculative security patch was applied. The acceptance-critical canonicalization,
crypto, policy, protocol, executor and model source contents are unchanged from the baseline.
Regression tests preserve the attempted attacks and deliberately broken assumptions.

Unfinished engineering issues were corrected: GPU CLI commands were added, the manual
freeze command now selects the explicit experiment schema for the loaded policy, and
benchmark typing/formatting was completed. The Qiskit 2.5.2/Aer GPU 0.15.1 import failure
was resolved with the tested 1.4.6 compatibility pin before the baseline. None of these
is presented as an exploitable authorization bypass.

## Claims that must be narrower

- A policy-file edit is not live revocation. Constructed executors hold immutable trust
  snapshots. Replace/restart the executor with the new trusted configuration to revoke
  acceptance. Existing permits cannot be silently reinterpreted under changed contents;
  an old in-memory executor can still apply its old policy until explicitly reconfigured.
- Replay is at-most-once admission within one protected, non-rolled-back shared database.
  We concretely executed a receipt twice with two databases and after administrator
  restoration of a pre-use snapshot. Signatures do not repair lost replay state.
- A result signature proves an executor-key assertion. A deliberately lying trusted
  adapter produced false counts with valid provenance, and possession of the executor
  key allowed historical-looking signed output without running the experiment.
  This is neither proof of computation nor independently authenticated time.
- A backend revision is a logical adapter contract. It does not cryptographically attest
  the loaded Python binary, provider build, GPU firmware or driver. Exact package locks
  aid reproduction but are not hardware/software attestation.
- Signatures bind canonical action semantics. Another valid signature over the same
  intent is acceptable; byte-level identity of the signature envelope is not required.
- Limits are per action. There is no cumulative resource budget, external physical-evidence
  oracle, multi-host consensus, production admission controller or denial-of-service SLA.

## Claims supported by these observations

Under the stated trust assumptions, the tested exact-action, policy-content, suite,
quorum and audience bindings held. Requested GPU execution could not silently switch
to CPU. Signed false evidence did not override deterministic executor policy.
Simultaneously issued distinct receipts for the same nonce admitted one execution.
Finite successes support these tested behaviors only; they do not rule out other attacks.

## Reproduction

```bash
cd ~/proofgate-pq
source ~/miniforge3/etc/profile.d/conda.sh
conda activate proofgate-pq
python scripts/redteam.py
python scripts/stress_authorization.py
PROOFGATE_GPU_TESTS=1 python -m pytest -q --junitxml=reports/tests-gpu.xml
```

Tests showing assumption violations run only in fresh temporary directories and do not
delete or restore real deployment databases. Never copy those steps into a live executor.
