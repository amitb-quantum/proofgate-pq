# Measured CPU/GPU comparison

NVIDIA GeForce RTX 5090, 32607 MiB, 610.74, 12.0

Numbers below are measured median milliseconds; distributions and warmups are in JSON.

| Qubits | Gates | CPU ms | GPU ms | CPU/GPU ratio |
|---|---:|---:|---:|---:|
| 2 | 5 | 0.563 | 1.606 | 0.35 |
| 16 | 376 | 9.864 | 9.919 | 0.99 |
| 20 | 472 | 63.581 | 17.612 | 3.61 |
| 24 | 568 | 1251.097 | 125.364 | 9.98 |

Ratio >1 favors GPU; ratio <1 favors CPU. This is fixed-method statevector work.
The first GPU execution is reported separately, not hidden in warmed timings.

## Original two-qubit Bell circuit

| Method | Median ms |
|---|---:|
| CPU_stabilizer | 0.537 |
| CPU_statevector | 0.387 |
| GPU_statevector | 1.493 |

## Synthetic numeric predicate prefilter

| Rows | CPU ms | GPU resident ms | GPU including transfers ms |
|---|---:|---:|---:|
| 1024 | 0.012 | 0.148 | 0.264 |
| 100000 | 0.723 | 0.289 | 0.760 |
| 1000000 | 17.653 | 0.555 | 3.365 |

This prefilter does not authenticate evidence or authorize execution.

## Mean/std/p95 reduction

| Values | CPU ms | GPU including transfers ms |
|---|---:|---:|
| 30 | 0.064 | 0.378 |
| 1000000 | 8.982 | 1.883 |

## Methodology

```json
{
  "trials": 7,
  "warmups_per_workload": 2,
  "clock": "perf_counter_ns",
  "device_order": "alternating each trial",
  "gpu_synchronization": "Aer .result(); CuPy null stream synchronize before/after timing",
  "first_call": "separate first CPU/GPU backend execution; excluded from steady state",
  "quantum_boundary": "includes circuit construction, Aer run and completion",
  "batch_boundary": "GPU resident separate from host-upload/compute/download",
  "no_gpu_comparison": [
    "PQC signatures",
    "canonical SHA-384 hashing",
    "full authorization",
    "full adversarial corpus"
  ],
  "array_preflight": "CPU/GPU equality checks precede warmups and may initialize/JIT kernels"
}
```

No GPU signature or hashing acceleration is claimed here.
See gateway-gpu-benchmark.md for the measured full protected workflow.
No extrapolation beyond measured workload sizes. p05/p95 are empirical small-sample
quantiles, not latency guarantees. Desktop scheduling and GPU activity can add variance.
