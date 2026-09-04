# Reproducing measurements

Run `python -m proofgate benchmark --samples 20 --process-samples 3` in the locked
Python environment. This writes `reports/benchmark.json` and derives `reports/benchmark.md`
from those exact raw values. The renderer can be rerun via
`python -c "from pathlib import Path; from proofgate.benchmark import render_report; render_report(Path('reports/benchmark.json'))"`.

Use an otherwise idle host for meaningful comparison. The run records UTC date, CPU
description, logical CPU count, OS, Python, cryptography version and bundled OpenSSL.
Key generation/sign/verify samples measure the actual suite API, including key import,
raw key export and base64 conversion where applicable. They do not measure only the C
primitive. Each suite signs a 1024-character application payload inside a domain-separated
envelope; signed byte lengths are recorded per suite. One sign/verify warmup is excluded.

Quorum timing is three sequential in-process verifier calls, each verifying the request,
checking policy, signing evidence and validating its newly made signature against its
provisioned public key. Full authorization includes freeze, requester signing, header
creation, all three attestations, coordinator assembly and independent receipt verification.
It excludes initial key provisioning, replay reservation, simulator and result signing.

The separate process measurement repeats full authorization with three concurrently
launched fresh Python verifier processes. It includes interpreter startup, public trust
and individual private key loading, JSON IPC and final verification. This is deliberately
a local end-to-end measurement, not a network service or warm-worker benchmark.

Reports include raw sample arrays, minimum, median, maximum and an empirical p95 order
statistic. With only three process samples, p95 is effectively the maximum, not a reliable
tail estimator. Throughput is completed serial operations divided by summed measured
elapsed time. No parallel capacity, confidence interval or stable performance claim follows.

Receipt sizes include all three attestations even for 2-of-3 authorization. Raw public-key
and signature sizes sum both components for hybrid; JSON/base64 overhead is reported in
the receipt size. No SLH-DSA/ML-KEM values are invented or extrapolated.
