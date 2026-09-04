# Measured benchmark results

Environment: `{'timestamp': '2026-09-04T22:47:05Z', 'python': '3.12.10', 'platform': 'Windows-11-10.0.26200-SP0', 'machine': 'AMD64', 'processor': 'Intel64 Family 6 Model 198 Stepping 2, GenuineIntel', 'logical_cpus': 24, 'openssl': 'OpenSSL 4.0.1 9 Jun 2026', 'cryptography': '49.0.0'}`

Timings: median milliseconds. Key/signature sizes: combined raw component bytes.
Receipt size is canonical JSON including base64 signatures and all three attestations.

| Suite | Keygen ms | Sign ms | Verify ms | PK bytes | Sig bytes | Receipt bytes |
|---|---:|---:|---:|---:|---:|---:|
| ed25519-v1 | 0.025 | 0.036 | 0.049 | 32 | 64 | 3367 |
| mldsa65-v1 | 0.118 | 0.570 | 0.115 | 1952 | 3309 | 16345 |
| ed25519-mldsa65-v1 | 0.141 | 0.539 | 0.166 | 1984 | 3373 | 16680 |

| Suite | 3-vote ms | Full auth ms | Process auth ms | Auth/s | Process auth/s |
|---|---:|---:|---:|---:|---:|
| ed25519-v1 | 0.976 | 2.640 | 485.519 | 369.5 | 1.70 |
| mldsa65-v1 | 2.901 | 7.697 | 781.090 | 126.4 | 0.86 |
| ed25519-mldsa65-v1 | 3.426 | 8.944 | 490.531 | 111.8 | 1.87 |

## Methodology

```json
{
  "samples": 30,
  "process_samples": 5,
  "application_payload_bytes": 1024,
  "clock": "perf_counter_ns",
  "quorum": "2-of-3; all three votes included",
  "keygen": "suite generation plus raw/base64 export",
  "sign_verify": "suite API including raw key import and base64 serialization",
  "quorum_latency": "three sequential independent node functions, no IPC",
  "authorization": "freeze+request signing+3 votes+assembly+independent verification",
  "process_authorization": "same with three concurrent fresh OS processes and IPC",
  "throughput": "serial completed authorization operations / measured elapsed time",
  "excludes": "provisioning, replay storage, simulator, result signing; no network"
}
```

Small local samples describe this implementation and machine.
Process startup dominates IPC. No warm process pool, load/concurrency benchmark,
confidence interval or FIPS validation is claimed. Raw samples include outliers.
