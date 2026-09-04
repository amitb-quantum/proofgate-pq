"""High-volume CPU authorization/attack exercise; no GPU signature implementation is claimed."""

import argparse
import json
import statistics
import tempfile
import time
from pathlib import Path

from proofgate.attacks import issue, material
from proofgate.canonical import canonical, digest, parse
from proofgate.errors import GateError
from proofgate.local import bell_experiment, freeze, load_key, sign_intent
from proofgate.models import Intent
from proofgate.protocol import verify_receipt


def run(output, batches=5, per_batch=400, warmups=20):
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with tempfile.TemporaryDirectory(prefix="signed-stress-", dir=output.parent) as directory:
        root = Path(directory) / "cluster"
        trust, _, _ = material(root)
        key = load_key(root, "scientist")

        def attempt(index):
            request = sign_intent(freeze(bell_experiment(), trust), key)
            receipt = issue(root, trust, request)
            if index % 2:
                raw = request.intent.model_dump()
                # Validly re-sign correlated changes; original receipt must reject them.
                raw["parameters"]["experiment"]["seed"] += index + 1
                raw["parameters"]["frozen_digest"] = digest(
                    "experiment", raw["parameters"]["experiment"]
                )
                raw["context"]["project"] = "different-project"
                request = sign_intent(parse(Intent, canonical(raw)), key)
            try:
                verify_receipt(canonical(request), canonical(receipt), trust, int(time.time()))
                return "ALLOW"
            except GateError as exc:
                return exc.code

        warm_start = time.perf_counter_ns()
        for index in range(warmups):
            assert attempt(index) == ("ACTION_MISMATCH" if index % 2 else "ALLOW")
        warm_ms = (time.perf_counter_ns() - warm_start) / 1e6
        for batch in range(batches):
            start = time.perf_counter_ns()
            outcomes = []
            for index in range(per_batch):
                actual = attempt(index)
                assert actual == ("ACTION_MISMATCH" if index % 2 else "ALLOW")
                outcomes.append(actual)
            elapsed_ms = (time.perf_counter_ns() - start) / 1e6
            rows.append(
                {
                    "batch": batch,
                    "elapsed_ms": elapsed_ms,
                    "outcomes": outcomes,
                    "attempts_per_second": per_batch * 1000 / elapsed_ms,
                }
            )
    report = {
        "device": "CPU",
        "batches": batches,
        "attempts_per_batch": per_batch,
        "total_attempts": batches * per_batch,
        "warmup_attempts": warmups,
        "warmup_ms": warm_ms,
        "raw": rows,
        "median_batch_ms": statistics.median(r["elapsed_ms"] for r in rows),
        "median_attempts_per_second": statistics.median(r["attempts_per_second"] for r in rows),
        "min_batch_ms": min(r["elapsed_ms"] for r in rows),
        "max_batch_ms": max(r["elapsed_ms"] for r in rows),
        "scope": "fresh hybrid request, 3 verifier signatures, assembly and receipt check; "
        "half are correlated requester-resigned attacks; no execution or GPU comparison",
    }
    output.write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("reports/signed-stress.json"))
    parser.add_argument("--batches", type=int, default=5)
    parser.add_argument("--per-batch", type=int, default=400)
    args = parser.parse_args()
    result = run(args.output, args.batches, args.per_batch)
    print(
        result["total_attempts"],
        "attempts passed;",
        result["median_attempts_per_second"],
        "per second",
    )
