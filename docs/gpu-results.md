# GPU workload and measured decision

The useful GPU demonstration is a 24-qubit, 568-gate, 8-layer H/T/CX circuit with
1024 shots and fixed generation/sampling seeds. T gates make this a non-Clifford
workload; its double-precision statevector is 256 MiB. It is large enough to amortize
GPU dispatch while remaining far below the RTX 5090's reported 32607 MiB capacity.

A version-2 frozen specification and policy bind the exact Aer CPU/GPU backend.
The same protected executor validates hybrid 3-of-3 evidence, reserves the nonce in
SQLite, invokes the selected backend and signs provenance. There is no paid QPU or
cloud use, no unsigned device selection and no GPU-to-CPU fallback.

## Measured results

Seven steady-state trials followed two warmups per workload. Raw data records every
trial, excluded warmup, min/max, mean/stdev, median and p05/p95, along with device metadata.
Aer .result() waits for completion; CuPy measurements synchronize before/after the call.
First backend execution and initialization/import overhead are separate in raw reports.
These are fixed-thread reference measurements, not a claim of optimal CPU tuning.

| Workload | CPU median | GPU median | Observation |
|---|---:|---:|---|
| 2-qubit non-Clifford test | 0.563 ms | 1.606 ms | GPU slower |
| 16-qubit statevector | 9.864 ms | 9.919 ms | Roughly tied |
| 20-qubit statevector | 63.581 ms | 17.612 ms | GPU 3.61x faster |
| 24-qubit statevector | 1251.097 ms | 125.364 ms | GPU 9.98x faster |
| Complete protected 24-qubit workflow | 1421.534 ms | 274.465 ms | GPU 5.18x faster overall |

The reference CPU backend uses eight OpenMP threads. A separate all-24-thread sensitivity
run measured a 1240.595 ms median (seven trials, two warmups), similar to the eight-thread
reference. Raw data is in reports/cpu-thread-sensitivity.json; it is not substituted
into the fixed-backend measurements. The inventory/CuPy import and inspection took 1037.427 ms; the subsequent first Aer GPU
backend call took 29.715 ms for the tiny circuit. Neither is in the warmed simulation
medians. These are first-use phases in this run, not a cold-machine/JIT-cache guarantee.

The complete workflow includes request creation/signing, three fresh verifier processes,
independent receipt verification, durable SQLite reservation, simulation, result signing
and provenance verification. Median authorization itself was approximately 114 ms on both
paths; it stays on CPU. One-time provisioning and adapter/executor construction are
excluded from steady-state totals and recorded separately where applicable.

For the original Bell circuit, CPU statevector took 0.387 ms, CPU stabilizer 0.537 ms and
GPU statevector 1.493 ms. Keep the tiny default example on CPU; GPU is optional for the
larger versioned demonstration.

## Other GPU candidates

A synthetic one-million-row numeric resource-predicate prefilter measured 17.653 ms
on NumPy CPU versus 3.365 ms on GPU including transfers (resident GPU: 0.555 ms).
At 1024 rows GPU lost, and at 100000 rows transfer-inclusive GPU was slightly slower.
This prefilter is an experiment, not trusted policy, signature verification or authorization.

A mean/std/p95 reduction over one million synthetic values took 8.982 ms on CPU and
1.883 ms on GPU including transfers. For a synthetic array with the original report's 30-sample count,
CPU took 0.064 ms and GPU 0.378 ms, so report generation remains CPU.

No suitable maintained GPU SHA-384/protocol-signature integration was established.
PyCA signature APIs are CPU here. No GPU cryptographic acceleration, unmeasured hashing
benefit or full adversarial-corpus GPU speedup is claimed.

## Artifacts and commands

- reports/gpu-benchmark.json and .md: simulation, prefilter and statistics samples.
- reports/gateway-gpu-benchmark.json and .md: complete protected CPU/GPU workflow.
- reports/quantum-gpu/: public request, receipt, result and GPU execution metadata.
- reports/signed-stress.json: 2000 actual CPU signed authorization/attack attempts.

```bash
python -m proofgate --root .demo-gpu-new gpu-demo --qubits 24 --layers 8 --device GPU
python -m proofgate gpu-benchmark --trials 7 --warmups 2
python -m proofgate gateway-benchmark --trials 7 --warmups 2
python -m proofgate --root reports/quantum-gpu verify-result
python scripts/cpu_thread_sensitivity.py
```

Software/driver installation inspection and compatibility details are in environment/README.md.
The GPU wheel uses Aer CUDA/Thrust; metadata explicitly reports cuStateVec_enable=false.
Qiskit 1.4.6 is required by the installed Aer GPU wheel and emits deprecation warnings.
Small-sample quantiles and desktop scheduling do not establish production latency guarantees.

Primary implementation references: [Aer GPU API](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html),
[Aer installation](https://qiskit.github.io/qiskit-aer/getting_started.html),
[CuPy environment-local CUDA installation](https://docs.cupy.dev/en/stable/install.html).
