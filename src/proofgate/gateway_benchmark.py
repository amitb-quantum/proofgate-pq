"""Full protected CPU/GPU path; every measured run obtains and spends a fresh receipt."""

import json
import tempfile
import time
from pathlib import Path
from typing import Any, Literal

from .accelerated import provision_accelerated, workload
from .aer import AerAdapter
from .canonical import canonical
from .executor import ProtectedExecutor, ReplayStore, verify_result
from .gpu_benchmark import inventory, stats, timed
from .local import authorize_processes, freeze, load_key, sign_intent


def benchmark_gateway(output: Path, trials: int = 7, warmups: int = 2) -> dict[str, Any]:
    from .errors import require

    require(trials >= 3 and warmups >= 1, "BENCHMARK_SAMPLE_LIMIT")
    output.parent.mkdir(parents=True, exist_ok=True)
    devices: list[Literal["CPU", "GPU"]] = ["CPU", "GPU"]
    report: dict[str, Any] = {
        "environment": inventory(),
        "workload": {"qubits": 24, "layers": 8, "gates": 568, "shots": 1024},
        "methodology": {
            "trials": trials,
            "warmups_per_device": warmups,
            "order": "alternating",
            "clock": "perf_counter_ns",
            "suite": "ed25519-mldsa65-v1",
            "quorum": "3-of-3",
            "included": "freeze/sign, three fresh verifier processes, executor receipt check, "
            "SQLite FULL reservation, simulation, result signing, provenance verification",
            "excluded": "key provisioning; adapter/executor construction recorded separately",
            "initialization": "first full run per device separately recorded before warmups",
            "synchronization": "Aer job .result() waits for CPU/GPU completion",
            "replay": "fresh intent nonce and receipt per run; same persistent database per device",
        },
        "devices": {},
    }
    with tempfile.TemporaryDirectory(prefix="proofgate-full-", dir=output.parent) as directory:
        state = {}
        for device in devices:
            root = Path(directory) / device.lower()
            trust = provision_accelerated(root, device)
            spec = workload(24, 8, device)
            adapter, adapter_ms = timed(lambda: AerAdapter(device))
            executor, executor_ms = timed(
                lambda: ProtectedExecutor(
                    trust, load_key(root, "executor"), ReplayStore(root / "replay.sqlite"), adapter
                )
            )
            state[device] = (root, trust, spec, adapter, executor)
            report["devices"][device] = {
                "adapter_constructor_ms": adapter_ms,
                "executor_constructor_ms": executor_ms,
                "warmups": [],
                "raw": [],
            }

        def one(device: Literal["CPU", "GPU"]) -> dict[str, Any]:
            root, trust, spec, adapter, executor = state[device]
            started = time.perf_counter_ns()
            request = sign_intent(freeze(spec, trust), load_key(root, "scientist"))
            signed = time.perf_counter_ns()
            receipt, nodes = authorize_processes(root, request)
            authorized = time.perf_counter_ns()
            record = executor.execute(canonical(request), canonical(receipt))
            executed = time.perf_counter_ns()
            verify_result(canonical(record), canonical(request), canonical(receipt), trust)
            checked = time.perf_counter_ns()
            return {
                "request_ms": (signed - started) / 1e6,
                "authorization_ms": (authorized - signed) / 1e6,
                "protected_execute_ms": (executed - authorized) / 1e6,
                "provenance_verify_ms": (checked - executed) / 1e6,
                "total_ms": (checked - started) / 1e6,
                "adapter": adapter.last_metrics.copy(),
                "nodes": nodes,
                "counts_total": sum(record.body.counts.values()),
                "intent_nonce": request.intent.nonce,
                "receipt_id": receipt.header.receipt_id,
            }

        for device in devices:
            report["devices"][device]["first_run"] = one(device)
        for _ in range(warmups):
            for device in devices:
                report["devices"][device]["warmups"].append(one(device))
        for trial in range(trials):
            for device in devices if trial % 2 == 0 else list(reversed(devices)):
                report["devices"][device]["raw"].append(one(device))
        for data in report["devices"].values():
            data["summary_ms"] = {
                field: stats([row[field] for row in data["raw"]])
                for field in [
                    "request_ms",
                    "authorization_ms",
                    "protected_execute_ms",
                    "provenance_verify_ms",
                    "total_ms",
                ]
            }
    report["cpu_over_gpu_median_ratio"] = (
        report["devices"]["CPU"]["summary_ms"]["total_ms"]["median"]
        / report["devices"]["GPU"]["summary_ms"]["total_ms"]["median"]
    )
    output.write_text(json.dumps(report, indent=2) + "\n")
    lines = [
        "# Complete protected CPU/GPU workflow",
        "",
        "24 qubits, 568 H/T/CX gates, 1024 shots, hybrid 3-of-3 authorization.",
        "Seven measured fresh permits per device after two warmups; medians in milliseconds.",
        "",
        "| Device | Request | Authorization | Protected execute | Provenance verify | Total |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for device, row in report["devices"].items():
        s = row["summary_ms"]
        cells = [
            f"{s[key]['median']:.3f}"
            for key in [
                "request_ms",
                "authorization_ms",
                "protected_execute_ms",
                "provenance_verify_ms",
                "total_ms",
            ]
        ]
        lines.append("| " + device + " | " + " | ".join(cells) + " |")
    lines += [
        "",
        f"Measured total CPU/GPU median ratio: {report['cpu_over_gpu_median_ratio']:.2f}.",
        "",
        "The GPU accelerates simulation. Signatures, quorum, JSON and SQLite still use CPU.",
        "First-run latency, construction, warmups, raw samples, distribution statistics and",
        "actual GPU device metadata are retained in the adjacent JSON file.",
    ]
    output.with_suffix(".md").write_text("\n".join(lines) + "\n")
    return report
