"""Actual CPU/GPU timings. Experimental vectorized filtering never grants authorization."""

import contextlib
import importlib.metadata
import io
import json
import platform
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from .accelerated import workload
from .aer import AerAdapter, circuit_for
from .errors import require


def stats(values: list[float]) -> dict[str, float]:
    import numpy as np

    a = np.asarray(values, dtype=np.float64)
    return {
        "median": float(np.median(a)),
        "p05": float(np.percentile(a, 5)),
        "p95": float(np.percentile(a, 95)),
        "min": float(a.min()),
        "max": float(a.max()),
        "mean": float(a.mean()),
        "stdev": float(a.std(ddof=1)) if len(a) > 1 else 0.0,
    }


def timed(call: Callable[[], Any], sync: Callable[[], Any] | None = None) -> tuple[Any, float]:
    if sync:
        sync()
    start = time.perf_counter_ns()
    value = call()
    if sync:
        sync()
    return value, (time.perf_counter_ns() - start) / 1e6


def inventory() -> dict[str, Any]:
    import cupy as cp

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cp.show_config()
    gpu = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,driver_version,compute_cap",
            "--format=csv,noheader",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "gpu": gpu,
        "cuda_driver_api": cp.cuda.runtime.driverGetVersion(),
        "cuda_runtime": cp.cuda.runtime.runtimeGetVersion(),
        "cupy_configuration": buf.getvalue(),
        "packages": {
            name: importlib.metadata.version(name)
            for name in ["qiskit", "qiskit-aer-gpu", "cupy-cuda12x", "numpy", "cryptography"]
        },
    }


def run_quantum(trials: int, warmups: int) -> dict[str, Any]:
    import numpy as np
    from qiskit_aer import AerSimulator

    result: dict[str, Any] = {"workloads": [], "initialization": {}}
    adapters: dict[Literal["CPU", "GPU"], AerAdapter] = {}
    devices: list[Literal["CPU", "GPU"]] = ["CPU", "GPU"]
    for device in devices:
        adapter, construction_ms = timed(lambda: AerAdapter(device))
        adapters[device] = adapter
        adapter.run(workload(2, 1, device))
        result["initialization"][device] = {
            "constructor_ms": construction_ms,
            "first_execution": adapter.last_metrics.copy(),
            "note": "first backend execution in this process, before workload warmups",
        }
    # Independent small-state correctness check including complex T-gate amplitudes.
    spec = workload(8, 3, "CPU")
    qc = circuit_for(spec).remove_final_measurements(inplace=False)
    qc.save_statevector()
    states = []
    for device in devices:
        output = adapters[device].backend.run(qc).result()
        require(output.success, "SIMULATOR_FAILED")
        states.append(np.asarray(output.get_statevector()))
    maximum_error = float(np.max(np.abs(states[0] - states[1])))
    require(bool(np.allclose(states[0], states[1], rtol=1e-12, atol=1e-12)), "GPU_CORRECTNESS")
    result["correctness"] = {"qubits": 8, "layers": 3, "max_amplitude_error": maximum_error}
    for qubits, layers in [(2, 1), (16, 8), (20, 8), (24, 8)]:
        specs = {device: workload(qubits, layers, device) for device in adapters}
        warm: dict[str, list[Any]] = {device: [] for device in adapters}
        raw: dict[str, list[Any]] = {device: [] for device in adapters}
        for _ in range(warmups):
            for device, adapter in adapters.items():
                adapter.run(specs[device])
                warm[device].append(adapter.last_metrics.copy())
        for trial in range(trials):
            order: list[Literal["CPU", "GPU"]] = (
                ["CPU", "GPU"] if trial % 2 == 0 else ["GPU", "CPU"]
            )
            for device in order:
                adapter = adapters[device]
                counts = adapter.run(specs[device])
                require(sum(counts.values()) == specs[device].shots, "RESULT_COUNTS_INVALID")
                raw[device].append(adapter.last_metrics.copy())
        summary = {device: stats([r["total_ms"] for r in rows]) for device, rows in raw.items()}
        result["workloads"].append(
            {
                "qubits": qubits,
                "layers": layers,
                "gates": len(specs["CPU"].gates),
                "shots": 1024,
                "statevector_bytes": 16 * 2**qubits,
                "precision": "double",
                "method": "statevector",
                "cpu_threads": 8,
                "warmups": warm,
                "raw": raw,
                "summary_ms": summary,
                "cpu_over_gpu_median_ratio": summary["CPU"]["median"] / summary["GPU"]["median"],
            }
        )
    # Bell is Clifford: measure an appropriate CPU alternative rather than suggesting
    # GPU statevector is the fastest possible approach for the original two-qubit demo.
    from qiskit import QuantumCircuit

    bell = QuantumCircuit(2)
    bell.h(0)
    bell.cx(0, 1)
    bell.measure_all()
    bell_rows = {}
    for label, backend in [
        ("CPU_stabilizer", AerSimulator(method="stabilizer", max_parallel_threads=8)),
        ("CPU_statevector", adapters["CPU"].backend),
        ("GPU_statevector", adapters["GPU"].backend),
    ]:

        def call() -> None:
            output = backend.run(bell, shots=1024, seed_simulator=7).result()
            require(output.success, "SIMULATOR_FAILED")
            require(set(output.get_counts()) <= {"00", "11"}, "GPU_CORRECTNESS")

        bell_warm = [timed(call)[1] for _ in range(warmups)]
        bell_raw = [timed(call)[1] for _ in range(trials)]
        bell_rows[label] = {
            "raw_ms": bell_raw,
            "warmup_ms": bell_warm,
            "summary_ms": stats(bell_raw),
        }
    result["bell"] = {"qubits": 2, "gates": 2, "shots": 1024, "measurements": bell_rows}
    return result


def run_arrays(trials: int, warmups: int) -> dict[str, Any]:
    import cupy as cp
    import numpy as np

    sync = cp.cuda.Stream.null.synchronize

    def predicate(x: Any) -> Any:
        return (
            (x[:, 0] >= 1)
            & (x[:, 0] <= 26)
            & (x[:, 1] >= 1)
            & (x[:, 1] <= 4096)
            & (x[:, 2] >= 0)
            & (x[:, 2] < x[:, 0])
            & (x[:, 3] > x[:, 4])
            & (x[:, 4] >= 0)
        )

    rows = []
    data: Any
    rng = np.random.default_rng(173)
    for size in [1024, 100_000, 1_000_000]:
        data = rng.integers(0, 6000, size=(size, 5), dtype=np.int64)
        data[:, 0] %= 40
        data[:, 2] %= 40
        gpu, upload_ms = timed(lambda: cp.asarray(data), sync)
        correct = predicate(data)
        require(bool(np.array_equal(cp.asnumpy(predicate(gpu)), correct)), "GPU_CORRECTNESS")
        functions = {
            "CPU": lambda: predicate(data),
            "GPU_resident": lambda: predicate(gpu),
            "GPU_end_to_end": lambda: cp.asnumpy(predicate(cp.asarray(data))),
        }
        raw: dict[str, list[float]] = {key: [] for key in functions}
        warm: dict[str, list[float]] = {key: [] for key in functions}
        for key, fn in functions.items():
            for _ in range(warmups):
                warm[key].append(timed(fn, sync if key != "CPU" else None)[1])
        for trial in range(trials):
            order = list(functions) if trial % 2 == 0 else list(reversed(functions))
            for key in order:
                raw[key].append(timed(functions[key], sync if key != "CPU" else None)[1])
        rows.append(
            {
                "rows": size,
                "columns": 5,
                "input_bytes": data.nbytes,
                "upload_ms": upload_ms,
                "warmups_ms": warm,
                "raw_ms": raw,
                "summary_ms": {k: stats(v) for k, v in raw.items()},
                "equality_checked": True,
            }
        )
    # Benchmark-analysis candidate: mean/std/p95 over actual-sized and larger synthetic arrays.
    analysis = []
    for size in [30, 1_000_000]:
        data = rng.lognormal(size=size)
        gpu = cp.asarray(data)

        def reduce(x: Any, xp: Any) -> Any:
            return xp.asarray([xp.mean(x), xp.std(x), xp.percentile(x, 95)])

        def gpu_e2e() -> Any:
            return cp.asnumpy(reduce(cp.asarray(data), cp))

        require(bool(np.allclose(reduce(data, np), gpu_e2e(), rtol=1e-10)), "GPU_CORRECTNESS")
        functions = {"CPU": lambda: reduce(data, np), "GPU_end_to_end": gpu_e2e}
        raw = {key: [] for key in functions}
        warm = {key: [] for key in functions}
        for key, fn in functions.items():
            for _ in range(warmups):
                warm[key].append(timed(fn, sync if key != "CPU" else None)[1])
        for trial in range(trials):
            for key in list(functions) if trial % 2 == 0 else list(reversed(functions)):
                raw[key].append(timed(functions[key], sync if key != "CPU" else None)[1])
        analysis.append(
            {
                "values": size,
                "input_bytes": data.nbytes,
                "warmups_ms": warm,
                "raw_ms": raw,
                "summary_ms": {k: stats(v) for k, v in raw.items()},
                "equality_checked": True,
            }
        )
    return {
        "predicate_prefilter": rows,
        "statistical_analysis": analysis,
        "scope": "synthetic numeric prefilters/reductions, not complete authorization or hashing",
    }


def benchmark_gpu(output: Path, trials: int = 7, warmups: int = 2) -> dict[str, Any]:
    require(trials >= 3 and warmups >= 1, "BENCHMARK_SAMPLE_LIMIT")
    started = time.perf_counter_ns()
    env = inventory()
    report = {
        "environment": env,
        "inventory_import_ms": (time.perf_counter_ns() - started) / 1e6,
        "methodology": {
            "trials": trials,
            "warmups_per_workload": warmups,
            "array_preflight": "Equality check may initialize/JIT kernels before warmups",
            "clock": "perf_counter_ns",
            "device_order": "alternating each trial",
            "gpu_synchronization": "Aer .result(); CuPy stream sync before/after timing",
            "first_call": "separate first CPU/GPU backend execution; excluded from steady state",
            "quantum_boundary": "includes circuit construction, Aer run and completion",
            "batch_boundary": "GPU resident separate from host-upload/compute/download",
            "no_gpu_comparison": [
                "PQC signatures",
                "canonical SHA-384 hashing",
                "full authorization",
                "full adversarial corpus",
            ],
        },
    }
    report["quantum"] = run_quantum(trials, warmups)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2) + "\n"
    )  # Preserve completed quantum measurements.
    report["arrays"] = run_arrays(trials, warmups)
    output.write_text(json.dumps(report, indent=2) + "\n")
    render_gpu_report(output)
    return report


def render_gpu_report(path: Path) -> None:
    report = json.loads(path.read_text())
    lines = [
        "# Measured CPU/GPU comparison",
        "",
        str(report["environment"]["gpu"]),
        "",
        "Numbers below are measured median milliseconds; distributions and warmups are in JSON.",
        "",
        "| Qubits | Gates | CPU ms | GPU ms | CPU/GPU ratio |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in report["quantum"]["workloads"]:
        s = row["summary_ms"]
        lines.append(
            f"| {row['qubits']} | {row['gates']} | {s['CPU']['median']:.3f} | "
            f"{s['GPU']['median']:.3f} | {row['cpu_over_gpu_median_ratio']:.2f} |"
        )
    lines += [
        "",
        "Ratio >1 favors GPU; ratio <1 favors CPU. This is fixed-method statevector work.",
        "The first GPU execution is reported separately, not hidden in warmed timings.",
        "",
        "## Original two-qubit Bell circuit",
        "",
        "| Method | Median ms |",
        "|---|---:|",
    ]
    for key, row in report["quantum"]["bell"]["measurements"].items():
        lines.append(f"| {key} | {row['summary_ms']['median']:.3f} |")
    lines += [
        "",
        "## Synthetic numeric predicate prefilter",
        "",
        "| Rows | CPU ms | GPU resident ms | GPU including transfers ms |",
        "|---|---:|---:|---:|",
    ]
    for row in report["arrays"]["predicate_prefilter"]:
        s = row["summary_ms"]
        lines.append(
            f"| {row['rows']} | {s['CPU']['median']:.3f} | "
            f"{s['GPU_resident']['median']:.3f} | {s['GPU_end_to_end']['median']:.3f} |"
        )
    lines += [
        "",
        "This prefilter does not authenticate evidence or authorize execution.",
        "",
        "## Mean/std/p95 reduction",
        "",
        "| Values | CPU ms | GPU including transfers ms |",
        "|---|---:|---:|",
    ]
    for row in report["arrays"]["statistical_analysis"]:
        s = row["summary_ms"]
        lines.append(
            f"| {row['values']} | {s['CPU']['median']:.3f} | {s['GPU_end_to_end']['median']:.3f} |"
        )
    lines += [
        "",
        "## Methodology",
        "",
        "```json",
        json.dumps(report["methodology"], indent=2),
        "```",
        "",
        "No GPU signature or hashing acceleration is claimed here.",
        "See gateway-gpu-benchmark.md for the measured full protected workflow.",
        "No extrapolation beyond measured workload sizes. p05/p95 are empirical small-sample",
        "quantiles, not latency guarantees. Desktop scheduling and GPU activity can add variance.",
    ]
    path.with_suffix(".md").write_text("\n".join(lines) + "\n")
