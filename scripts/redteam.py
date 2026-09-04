"""Concrete red-team reproductions. Run from this repository with the project interpreter."""

import argparse
import json
import shutil
import tempfile
import time
from pathlib import Path

from proofgate import crypto
from proofgate.attacks import issue, material, resign_vote
from proofgate.canonical import canonical, digest, parse, write
from proofgate.errors import GateError
from proofgate.executor import ProtectedExecutor, ReplayStore, verify_result
from proofgate.local import load_key, sign_intent
from proofgate.models import Intent, ResultBody, ResultRecord, TrustBundle
from proofgate.protocol import verify_receipt
from proofgate.simulator import StatevectorSimulator


def run(output: Path) -> dict:
    rows = []

    def record(name, classification, expected, call, boundary):
        try:
            actual = call()
        except GateError as exc:
            actual = exc.code
        rows.append(
            {
                "hypothesis": name,
                "classification": classification,
                "expected_observation": expected,
                "observed": actual,
                "reproduced": actual == expected,
                "boundary": boundary,
            }
        )

    with tempfile.TemporaryDirectory(prefix="redteam-", dir=output.parent) as directory:
        base = Path(directory)
        root = base / "cluster"
        trust, request, receipt = material(root)
        request_bytes, receipt_bytes = canonical(request), canonical(receipt)

        def check(req=request, rec=receipt, config=trust):
            verify_receipt(canonical(req), canonical(rec), config, int(time.time()))
            return "ALLOW"

        def resign_intent(raw):
            return sign_intent(parse(Intent, canonical(raw)), load_key(root, "scientist"))

        def all_compromised():
            data = request.intent.model_dump()
            data["target"] = "simulator:forbidden"
            changed = resign_intent(data)
            forged = issue(root, trust, changed).model_dump()
            forged["disposition"] = "ALLOW"
            for vote in forged["attestations"]:
                vote["body"]["disposition"] = "ALLOW"
                vote["body"]["predicates"] = {k: True for k in vote["body"]["predicates"]}
                resign_vote(vote, load_key(root, vote["body"]["verifier_id"]))
            return check(changed, forged)

        record(
            "all_three_signers_lie_about_denied_target",
            "CONFIRMED FAIL-CLOSED",
            "EVIDENCE_MISMATCH",
            all_compromised,
            "Stronger-than-model key compromise; executor deterministic policy still enforced",
        )

        def mix_headers():
            second = issue(root, trust, request)
            mixed = receipt.model_dump()
            mixed["attestations"][1] = second.attestations[1].model_dump()
            return check(rec=mixed)

        record(
            "mix_valid_attestations_from_different_issuances",
            "CONFIRMED FAIL-CLOSED",
            "ATTESTATION_HEADER_MISMATCH",
            mix_headers,
            "Untrusted coordinator; genuine signatures",
        )

        def freshly_signed_mutation():
            data = request.intent.model_dump()
            data["parameters"]["experiment"]["seed"] += 1
            data["parameters"]["frozen_digest"] = digest(
                "experiment", data["parameters"]["experiment"]
            )
            return check(resign_intent(data))

        record(
            "requester_resigns_changed_spec_with_old_receipt",
            "CONFIRMED FAIL-CLOSED",
            "ACTION_MISMATCH",
            freshly_signed_mutation,
            "Legitimate requester controls its own key",
        )

        def cross_role():
            raw = trust.model_dump()
            raw["verifiers"]["verifier-1"]["ml-dsa-65"] = raw["requesters"]["scientist"][
                "ml-dsa-65"
            ]
            return check(config=parse(TrustBundle, canonical(raw)))

        record(
            "share_only_pq_component_between_requester_and_verifier",
            "CONFIRMED FAIL-CLOSED",
            "TRUST_DUPLICATE_KEY",
            cross_role,
            "Invalid administrative trust configuration",
        )

        def raw_duplicate():
            raw = request_bytes.decode()
            raw = raw.replace(
                '"subject":"scientist"', '"subject":"scientist","\\u0073ubject":"attacker"'
            )
            verify_receipt(raw.encode(), receipt_bytes, trust, int(time.time()))
            return "ALLOW"

        record(
            "escaped_duplicate_security_field",
            "CONFIRMED FAIL-CLOSED",
            "DUPLICATE_JSON_KEY",
            raw_duplicate,
            "Untrusted raw JSON, decoded-key collision",
        )

        def bool_predicate():
            raw = receipt.model_dump()
            raw["attestations"][0]["body"]["predicates"]["circuit_well_formed"] = 1
            return check(rec=raw)

        record(
            "numeric_truthy_predicate_substitution",
            "CONFIRMED FAIL-CLOSED",
            "SCHEMA_INVALID",
            bool_predicate,
            "Untrusted JSON; Python bool/int equality attack",
        )

        def unknown_gate():
            raw = request.model_dump()
            raw["intent"]["parameters"]["experiment"]["gates"][0]["op"] = "__getattribute__"
            return check(req=raw)

        record(
            "dynamic_adapter_method_injection",
            "CONFIRMED FAIL-CLOSED",
            "SCHEMA_INVALID",
            unknown_gate,
            "Untrusted circuit operator",
        )

        def corrupt_surplus():
            raw = receipt.model_dump()
            raw["attestations"][2]["signatures"]["ml-dsa-65"] = crypto.encode(bytes(3309))
            return check(rec=raw)

        record(
            "two_valid_votes_plus_corrupt_surplus",
            "CONFIRMED FAIL-CLOSED",
            "SIGNATURE_INVALID",
            corrupt_surplus,
            "Threshold met, but included invalid evidence must reject",
        )

        def bootstrap_own_trust():
            _, req, rec = material(base / "other")
            return check(req, rec)

        record(
            "receipt_from_attacker_self_provisioned_cluster",
            "CONFIRMED FAIL-CLOSED",
            "SIGNATURE_INVALID",
            bootstrap_own_trust,
            "Executor retains genuine pinned keys",
        )

        def alternate_signature():
            changed = sign_intent(request.intent, load_key(root, "scientist"))
            return check(changed)

        record(
            "replace_request_signature_with_another_valid_signature",
            "DESIGN LIMITATION",
            "ALLOW",
            alternate_signature,
            "Same exact signed intent, no changed action; signature bytes not identity",
        )

        # Deliberately violate replay-store protection assumptions.
        def split_database():
            for name in ["split-a.sqlite", "split-b.sqlite"]:
                ProtectedExecutor(
                    trust, load_key(root, "executor"), ReplayStore(base / name)
                ).execute(request_bytes, receipt_bytes)
            return "EXECUTED_TWICE"

        record(
            "same_receipt_two_independent_replay_databases",
            "ASSUMPTION VIOLATION",
            "EXECUTED_TWICE",
            split_database,
            "Breaks the documented shared durable store assumption",
        )

        def restore_database():
            path = base / "rollback.sqlite"
            store = ReplayStore(path)
            store.reserve("unrelated", "unrelated", int(time.time()) + 300)
            snapshot = base / "before.sqlite"
            shutil.copyfile(path, snapshot)
            executor = ProtectedExecutor(trust, load_key(root, "executor"), store)
            executor.execute(request_bytes, receipt_bytes)
            shutil.copyfile(snapshot, path)
            executor.execute(request_bytes, receipt_bytes)
            return "EXECUTED_TWICE"

        record(
            "administrator_restores_preuse_database_snapshot",
            "ASSUMPTION VIOLATION",
            "EXECUTED_TWICE",
            restore_database,
            "Breaks rollback protection; no unsafely erased repository data",
        )

        def stale_policy():
            executor = ProtectedExecutor(
                trust, load_key(root, "executor"), ReplayStore(base / "stale.sqlite")
            )
            raw = trust.model_dump()
            raw["policy"]["target"] = "simulator:revoked"
            write(root / "trust.json", raw)
            executor.execute(request_bytes, receipt_bytes)
            write(root / "trust.json", trust)
            return "OLD_SNAPSHOT_EXECUTES"

        record(
            "edit_policy_file_after_executor_construction",
            "DESIGN LIMITATION",
            "OLD_SNAPSHOT_EXECUTES",
            stale_policy,
            "Executor pins an in-memory snapshot; file edits are not live revocation",
        )

        def fake_adapter():
            class LyingAdapter(StatevectorSimulator):
                def run(self, spec):
                    return {"00": spec.shots}  # Structurally valid, deliberately false result.

            result = ProtectedExecutor(
                trust, load_key(root, "executor"), ReplayStore(base / "lie.sqlite"), LyingAdapter()
            ).execute(request_bytes, receipt_bytes)
            verify_result(canonical(result), request_bytes, receipt_bytes, trust)
            return "FALSE_COUNTS_HAVE_VALID_SIGNATURE"

        record(
            "trusted_adapter_lies_about_computation",
            "ASSUMPTION VIOLATION",
            "FALSE_COUNTS_HAVE_VALID_SIGNATURE",
            fake_adapter,
            "Attestation is not proof of correct computation; malicious executor/runtime",
        )

        def forged_time():
            fake = ResultBody(
                schema_version=1,
                executor_id=trust.executor_id,
                suite=trust.policy.suite,
                audience=trust.policy.audience,
                action_digest=digest("intent", request.intent),
                frozen_digest=request.intent.parameters.frozen_digest,
                receipt_digest=digest("receipt", receipt),
                receipt_id=receipt.header.receipt_id,
                backend="builtin-statevector-v1",
                executed_at=receipt.header.issued_at,
                counts={"00": 1024},
            )
            key = load_key(root, "executor")
            result = ResultRecord(
                body=fake,
                signatures=crypto.sign(
                    key.suite,
                    key.private_keys,
                    crypto.message("result", key.suite, key.identity, fake),
                ),
            )
            verify_result(canonical(result), request_bytes, receipt_bytes, trust)
            return "SELF_ASSERTED_EXECUTION_TIME_ACCEPTED"

        record(
            "executor_key_forges_historical_result_without_running",
            "ASSUMPTION VIOLATION",
            "SELF_ASSERTED_EXECUTION_TIME_ACCEPTED",
            forged_time,
            "No independent timestamp or hardware/computation proof",
        )

        def header_extension():
            raw = receipt.model_dump()
            raw["header"]["expires_at"] += 1
            for vote in raw["attestations"]:
                vote["body"]["header"]["expires_at"] += 1
            return check(rec=raw)

        record(
            "coordinator_extends_every_header_without_resigning",
            "CONFIRMED FAIL-CLOSED",
            "RECEIPT_TTL",
            header_extension,
            "Untrusted coordinator; TTL cap catches before signatures",
        )

        # Fuzz bounded transport independently of the already tested leaf mutation strategy.
        def truncate_inputs():
            probes = 0
            for blob, is_request in [(request_bytes, True), (receipt_bytes, False)]:
                for point in sorted(
                    {0, 1, 2, len(blob) // 4, len(blob) // 2, len(blob) - 2, len(blob) - 1}
                ):
                    probes += 1
                    try:
                        verify_receipt(
                            blob[:point] if is_request else request_bytes,
                            receipt_bytes if is_request else blob[:point],
                            trust,
                            int(time.time()),
                        )
                    except GateError:
                        continue
                    return "UNEXPECTED_ACCEPT"
            return f"{probes}_REJECTED"

        record(
            "truncated_transport_prefixes",
            "CONFIRMED FAIL-CLOSED",
            "14_REJECTED",
            truncate_inputs,
            "Bounded raw-byte probes, zero protected executions",
        )

        def bounded_bypass_search():
            for index in range(32):
                data = request.intent.model_dump()
                data["parameters"]["experiment"]["seed"] += index + 1
                data["parameters"]["experiment"]["shots"] += index + 1
                data["parameters"]["frozen_digest"] = digest(
                    "experiment", data["parameters"]["experiment"]
                )
                changed = resign_intent(data)
                try:
                    check(changed)
                except GateError:
                    continue
                return "UNEXPECTED_BYPASS"
            return "NO_BYPASS_IN_32_TRIALS"

        record(
            "correlated_requester_resigned_mutation_bypass_search",
            "NOT REPRODUCED",
            "NO_BYPASS_IN_32_TRIALS",
            bounded_bypass_search,
            "Finite 32-trial search, no general security proof",
        )

    result = {
        "baseline": "702d66bcbfd65fa0bb584b5a882eadf613cb7a2c",
        "generated_at": int(time.time()),
        "findings": rows,
        "all_reproductions_match": all(r["reproduced"] for r in rows),
        "scope": "Concrete local attacks; not an independent audit or formal proof",
    }
    labels = [
        "CONFIRMED EXPLOITABLE",
        "CONFIRMED FAIL-CLOSED",
        "DESIGN LIMITATION",
        "ASSUMPTION VIOLATION",
        "NOT REPRODUCED",
    ]
    result["classification_counts"] = {
        label: sum(row["classification"] == label for row in rows) for label in labels
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    lines = [
        "# Red-team reproductions",
        "",
        f"Baseline: {result['baseline']}",
        "",
        "| Hypothesis | Classification | Observation |",
        "|---|---|---|",
    ]
    lines += [f"| {r['hypothesis']} | {r['classification']} | {r['observed']} |" for r in rows]
    lines += [
        "",
        "All classifications are scoped to the stated boundary. An assumption-violation",
        "reproduction is not evidence of a signature or receipt-verification bypass.",
        "No formal verification or security proof follows from rejected attacks.",
    ]
    output.with_suffix(".md").write_text("\n".join(lines) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("reports/redteam.json"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = run(args.output)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["all_reproductions_match"] else 1)
