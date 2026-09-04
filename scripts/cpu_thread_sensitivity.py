"""Direct CPU thread sensitivity; not a protected execution or backend revision change."""

import json
from pathlib import Path

from proofgate.accelerated import workload
from proofgate.aer import AerAdapter
from proofgate.gpu_benchmark import inventory, stats

if __name__ == "__main__":
    adapter = AerAdapter("CPU")
    adapter.backend.set_options(max_parallel_threads=24)
    spec = workload(24, 8, "CPU")
    warm = []
    raw = []
    for _ in range(2):
        adapter.run(spec)
        warm.append(adapter.last_metrics.copy())
    for _ in range(7):
        adapter.run(spec)
        raw.append(adapter.last_metrics.copy())
    report = {
        "environment": inventory(),
        "qubits": 24,
        "gates": 568,
        "shots": 1024,
        "cpu_threads": 24,
        "warmups": warm,
        "raw": raw,
        "summary_ms": stats([x["total_ms"] for x in raw]),
        "scope": "direct benchmark override; protected backend v1 remains fixed at 8 threads",
    }
    Path("reports/cpu-thread-sensitivity.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["summary_ms"])
