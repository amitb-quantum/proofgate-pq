"""Measured suite API timings including key serialization/load overhead; no fabricated data."""

import importlib.metadata
import json
import os
import platform
import statistics
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from cryptography.hazmat.backends.openssl.backend import backend

from . import crypto
from .canonical import canonical
from .local import authorize_processes, bell_experiment, freeze, load_key, provision, sign_intent
from .models import Suite
from .protocol import assemble, attest, new_header, verify_receipt


def _measure(call: Callable[[], Any]) -> tuple[Any, float]:
    start = time.perf_counter_ns()
    result = call()
    return result, (time.perf_counter_ns() - start) / 1_000_000


def benchmark(output: Path, samples: int = 20, process_samples: int = 3) -> dict[str, Any]:
    if samples < 2 or process_samples < 1:
        raise ValueError("At least two API samples and one process sample required")
    suites = []
    for name in crypto.SUITES:
        suite = cast(Suite, name)
        private, public = crypto.generate(suite)
        payload = crypto.message("benchmark", suite, "benchmark-key", {"payload": "x" * 1024})
        signature = crypto.sign(suite, private, payload)
        crypto.verify(suite, public, signature, payload)  # warm-up, excluded
        raw: dict[str, list[float]] = {
            k: []
            for k in [
                "keygen_ms",
                "sign_ms",
                "verify_ms",
                "quorum_ms",
                "authorization_ms",
                "process_authorization_ms",
            ]
        }
        with tempfile.TemporaryDirectory(prefix="proofgate-bench-") as directory:
            root = Path(directory) / "cluster"
            trust = provision(root, suite)
            requester = load_key(root, "scientist")
            keys = [load_key(root, i) for i in trust.policy.verifier_ids]
            receipt_size = 0
            for _ in range(samples):
                _, latency = _measure(lambda: crypto.generate(suite))
                raw["keygen_ms"].append(latency)
                signature, latency = _measure(lambda: crypto.sign(suite, private, payload))
                raw["sign_ms"].append(latency)
                _, latency = _measure(lambda: crypto.verify(suite, public, signature, payload))
                raw["verify_ms"].append(latency)
                start = time.perf_counter_ns()
                request = sign_intent(freeze(bell_experiment(), trust), requester)
                now = int(time.time())
                header = new_header(request, trust, now)
                votes, latency = _measure(
                    lambda: [attest(request, header, trust, k, now) for k in keys]
                )
                raw["quorum_ms"].append(latency)
                receipt = assemble(request, header, votes, trust, now)
                verify_receipt(canonical(request), canonical(receipt), trust, now)
                raw["authorization_ms"].append((time.perf_counter_ns() - start) / 1_000_000)
                receipt_size = len(canonical(receipt))
            for _ in range(process_samples):

                def process_authorization() -> None:
                    request = sign_intent(freeze(bell_experiment(), trust), requester)
                    receipt, _ = authorize_processes(root, request)
                    verify_receipt(canonical(request), canonical(receipt), trust, int(time.time()))

                _, latency = _measure(process_authorization)
                raw["process_authorization_ms"].append(latency)
        summary = {}
        for metric, values in raw.items():
            ordered = sorted(values)
            summary[metric] = {
                "median": statistics.median(values),
                "min": min(values),
                "max": max(values),
                "p95": ordered[min(len(values) - 1, int(0.95 * len(values)))],
            }
        suites.append(
            {
                "suite": suite,
                "signed_message_bytes": len(payload),
                "raw": raw,
                "summary": summary,
                "public_key_bytes": sum(len(crypto.unbase64(v)) for v in public.values()),
                "signature_bytes": sum(len(crypto.unbase64(v)) for v in signature.values()),
                "receipt_bytes": receipt_size,
                "serial_authorizations_per_second": 1000 * samples / sum(raw["authorization_ms"]),
                "serial_process_authorizations_per_second": 1000
                * process_samples
                / sum(raw["process_authorization_ms"]),
            }
        )
    report = {
        "environment": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "logical_cpus": os.cpu_count(),
            "openssl": backend.openssl_version_text(),
            "cryptography": importlib.metadata.version("cryptography"),
        },
        "methodology": {
            "samples": samples,
            "process_samples": process_samples,
            "application_payload_bytes": 1024,
            "clock": "perf_counter_ns",
            "quorum": "2-of-3; all three votes included",
            "keygen": "suite generation plus raw/base64 export",
            "sign_verify": "suite API including raw key import and base64 serialization",
            "quorum_latency": "three sequential independent node functions, no IPC",
            "authorization": "freeze+request signing+3 votes+assembly+independent verification",
            "process_authorization": "same with three concurrent fresh OS processes and IPC",
            "throughput": "serial completed authorization operations / measured elapsed time",
            "excludes": "provisioning, replay storage, simulator, result signing; no network",
        },
        "suites": suites,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    render_report(output)
    return report


def render_report(raw_path: Path) -> None:
    report = json.loads(raw_path.read_text(encoding="utf-8"))
    env = report["environment"]
    lines = [
        "# Measured benchmark results",
        "",
        f"Environment: `{env}`",
        "",
        "Timings: median milliseconds. Key/signature sizes: combined raw component bytes.",
        "Receipt size is canonical JSON including base64 signatures and all three attestations.",
        "",
        "| Suite | Keygen ms | Sign ms | Verify ms | PK bytes | Sig bytes | Receipt bytes |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["suites"]:
        m = row["summary"]
        lines.append(
            f"| {row['suite']} | {m['keygen_ms']['median']:.3f} | {m['sign_ms']['median']:.3f} | "
            f"{m['verify_ms']['median']:.3f} | {row['public_key_bytes']} | "
            f"{row['signature_bytes']} | {row['receipt_bytes']} |"
        )
    lines += [
        "",
        "| Suite | 3-vote ms | Full auth ms | Process auth ms | Auth/s | Process auth/s |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in report["suites"]:
        m = row["summary"]
        lines.append(
            f"| {row['suite']} | {m['quorum_ms']['median']:.3f} | "
            f"{m['authorization_ms']['median']:.3f} | "
            f"{m['process_authorization_ms']['median']:.3f} | "
            f"{row['serial_authorizations_per_second']:.1f} | "
            f"{row['serial_process_authorizations_per_second']:.2f} |"
        )
    lines += [
        "",
        "## Methodology",
        "",
        "```json",
        json.dumps(report["methodology"], indent=2),
        "```",
        "",
        "Small local samples describe this implementation and machine.",
        "Process startup dominates IPC. No warm process pool, load/concurrency benchmark,",
        "confidence interval or FIPS validation is claimed. Raw samples include outliers.",
    ]
    raw_path.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
