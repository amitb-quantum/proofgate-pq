import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .canonical import parse, read, write
from .errors import GateError
from .executor import ProtectedExecutor, ReplayStore, verify_result
from .local import (
    authorize_processes,
    freeze,
    load_key,
    load_trust,
    provision,
    sign_intent,
)
from .models import (
    Experiment,
    Intent,
    Receipt,
    ResultRecord,
    SignedIntent,
    TrustBundle,
)
from .protocol import inspect_receipt, verify_receipt


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ProofGate-PQ evidence-bound authorization prototype"
    )
    parser.add_argument("--root", type=Path, default=Path(".demo"))
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ["init", "quantum-demo"]:
        command = sub.add_parser(name)
        command.add_argument(
            "--suite",
            choices=["ed25519-v1", "mldsa65-v1", "ed25519-mldsa65-v1"],
            default="ed25519-mldsa65-v1",
        )
        command.add_argument("--quorum", type=int, choices=[2, 3], default=2)
    for name in [
        "freeze",
        "sign-intent",
        "authorize",
        "inspect",
        "verify",
        "execute",
        "verify-result",
    ]:
        sub.add_parser(name)
    attacks = sub.add_parser("attacks")
    attacks.add_argument("--output", type=Path, default=Path("reports/attacks.json"))
    bench = sub.add_parser("benchmark")
    bench.add_argument("--samples", type=int, default=20)
    bench.add_argument("--process-samples", type=int, default=3)
    bench.add_argument("--output", type=Path, default=Path("reports/benchmark.json"))
    schemas = sub.add_parser("schemas")
    schemas.add_argument("--output", type=Path, default=Path("schemas"))
    args = parser.parse_args()
    root = args.root
    try:
        result: Any = {"status": "OK", "command": args.command}
        if args.command == "init":
            provision(root, args.suite, args.quorum)
        elif args.command == "quantum-demo":
            from .demo import quantum_demo

            result = quantum_demo(root, args.suite, args.quorum)
        elif args.command == "attacks":
            from .attacks import run_corpus

            result = run_corpus(args.output)
            print(json.dumps(result, indent=2))
            return 0 if result["passed"] == result["total"] else 1
        elif args.command == "benchmark":
            from .benchmark import benchmark

            benchmark(args.output, args.samples, args.process_samples)
            result = {"report": str(args.output), "status": "MEASURED"}
        elif args.command == "schemas":
            args.output.mkdir(parents=True, exist_ok=True)
            schema_models: list[type[BaseModel]] = [
                Experiment,
                Intent,
                SignedIntent,
                Receipt,
                TrustBundle,
                ResultRecord,
            ]
            for model in schema_models:
                (args.output / f"{model.__name__}.schema.json").write_text(
                    json.dumps(model.model_json_schema(), indent=2) + "\n", encoding="utf-8"
                )
        else:
            trust = load_trust(root)
            if args.command == "freeze":
                write(
                    root / "intent.json",
                    freeze(parse(Experiment, read(root / "experiment.json")), trust),
                )
            elif args.command == "sign-intent":
                write(
                    root / "request.json",
                    sign_intent(
                        parse(Intent, read(root / "intent.json")), load_key(root, "scientist")
                    ),
                )
            elif args.command == "authorize":
                receipt, nodes = authorize_processes(
                    root, parse(SignedIntent, read(root / "request.json"))
                )
                write(root / "receipt.json", receipt)
                result = {"disposition": receipt.disposition, "nodes": nodes}
            elif args.command == "inspect":
                request = parse(SignedIntent, read(root / "request.json"))
                receipt = parse(Receipt, read(root / "receipt.json"))
                decision = inspect_receipt(request, receipt, trust, int(time.time()))
                result = {
                    "disposition": decision,
                    "header": receipt.header.model_dump(),
                    "evidence": [
                        {"verifier": a.body.verifier_id, "predicates": a.body.predicates}
                        for a in receipt.attestations
                    ],
                }
            elif args.command == "verify":
                verify_receipt(
                    read(root / "request.json"),
                    read(root / "receipt.json"),
                    trust,
                    int(time.time()),
                )
                result = {"authorization": "ALLOW", "replay_state": "not consumed or checked"}
            elif args.command == "execute":
                executor = ProtectedExecutor(
                    trust, load_key(root, "executor"), ReplayStore(root / "replay.sqlite")
                )
                record = executor.execute(read(root / "request.json"), read(root / "receipt.json"))
                write(root / "result.json", record)
                result = {"status": "EXECUTED", "counts": record.body.counts}
            elif args.command == "verify-result":
                verify_result(
                    read(root / "result.json"),
                    read(root / "request.json"),
                    read(root / "receipt.json"),
                    trust,
                )
                result = {"provenance": "VALID", "mode": "historical; does not authorize execution"}
        print(json.dumps(result, indent=2))
        return 0
    except GateError as exc:
        print(json.dumps({"status": "REJECTED", "code": exc.code}), file=sys.stderr)
        return 2
    except Exception:
        print(json.dumps({"status": "ERROR", "code": "INTERNAL_ERROR"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
