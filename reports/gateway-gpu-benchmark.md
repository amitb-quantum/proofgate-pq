# Complete protected CPU/GPU workflow

24 qubits, 568 H/T/CX gates, 1024 shots, hybrid 3-of-3 authorization.
Seven measured fresh permits per device after two warmups; medians in milliseconds.

| Device | Request | Authorization | Protected execute | Provenance verify | Total |
|---|---:|---:|---:|---:|---:|
| CPU | 2.364 | 114.933 | 1289.723 | 13.382 | 1421.534 |
| GPU | 2.189 | 113.635 | 141.708 | 13.278 | 274.465 |

Measured total CPU/GPU median ratio: 5.18.

The GPU accelerates simulation. Signatures, quorum, JSON and SQLite still use CPU.
First-run latency, construction, warmups, raw samples, distribution statistics and
actual GPU device metadata are retained in the adjacent JSON file.
