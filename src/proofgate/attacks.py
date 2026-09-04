"""Executable attack corpus; each case asserts a stable rejection reason or positive control."""

import copy
import tempfile
import time
from pathlib import Path
from typing import Any

from . import crypto
from .canonical import canonical, decode, parse, write
from .errors import GateError
from .executor import ProtectedExecutor, ReplayStore, verify_result
from .local import bell_experiment, freeze, load_key, provision, sign_intent
from .models import KeyFile, Receipt, SignedIntent, Suite, TrustBundle
from .protocol import assemble, attest, new_header, verify_receipt

# Public, stable attack inventory shared by CLI report and parameterized tests.
CASES = {
    "valid_authorization": "ALLOW",
    "modified_action_payload": "SIGNATURE_INVALID",
    "modified_target": "SIGNATURE_INVALID",
    "modified_receipt_nonce": "ATTESTATION_HEADER_MISMATCH",
    "wrong_public_key": "SIGNATURE_INVALID",
    "missing_required_signature": "SIGNATURE_COMPONENTS",
    "algorithm_downgrade": "SUITE_MISMATCH",
    "expired_receipt": "RECEIPT_EXPIRED",
    "future_receipt": "RECEIPT_FUTURE",
    "future_intent": "INTENT_FUTURE",
    "receipt_replay": "REPLAY",
    "insufficient_quorum": "DISPOSITION_MISMATCH",
    "duplicate_verifier": "VERIFIER_DUPLICATE",
    "unknown_verifier": "VERIFIER_UNKNOWN",
    "incorrect_policy_version": "POLICY_MISMATCH",
    "altered_frozen_experiment": "SIGNATURE_INVALID",
    "malformed_duplicate_json": "DUPLICATE_JSON_KEY",
    "signature_substitution": "SIGNATURE_INVALID",
    "one_malicious_verifier": "EVIDENCE_MISMATCH",
    "malicious_only_no_quorum": "DISPOSITION_MISMATCH",
    "two_honest_verifiers": "ALLOW",
    "policy_changed_same_version": "POLICY_DIGEST_MISMATCH",
    "receipt_threshold_downgrade": "QUORUM_MISMATCH",
    "receipt_suite_downgrade": "SUITE_MISMATCH",
    "evidence_mutation": "SIGNATURE_INVALID",
    "missing_evidence": "SIGNATURE_INVALID",
    "outer_disposition_mutation": "DISPOSITION_MISMATCH",
    "human_verify_not_approval": "NOT_ALLOW",
    "deny_not_approval": "NOT_ALLOW",
    "unknown_not_approval": "NOT_ALLOW",
    "error_not_approval": "DECISION_MISMATCH",
    "shared_identity_key": "TRUST_DUPLICATE_KEY",
    "extra_signature_algorithm": "SIGNATURE_COMPONENTS",
    "request_signature_missing": "SIGNATURE_COMPONENTS",
    "cross_domain_signature": "SIGNATURE_INVALID",
    "audience_swap": "AUDIENCE_MISMATCH",
    "extra_intent_field": "SCHEMA_INVALID",
    "float_canonical_input": "CANONICAL_NUMBER",
    "boolean_schema_version": "SCHEMA_INVALID",
    "result_tampering": "SIGNATURE_INVALID",
    "reissued_intent_replay": "REPLAY",
    "noncanonical_base64": "BASE64_INVALID",
    "expired_intent": "INTENT_EXPIRED",
    "signed_stale_freeze": "NOT_ALLOW",
}


def material(
    root: Path, suite: Suite = "ed25519-mldsa65-v1"
) -> tuple[TrustBundle, SignedIntent, Receipt]:
    trust = provision(root, suite)
    request = sign_intent(freeze(bell_experiment(), trust), load_key(root, "scientist"))
    return trust, request, issue(root, trust, request)


def issue(root: Path, trust: TrustBundle, request: SignedIntent) -> Receipt:
    now = int(time.time())
    header = new_header(request, trust, now)
    votes = [
        attest(request, header, trust, load_key(root, i), now) for i in trust.policy.verifier_ids
    ]
    return assemble(request, header, votes, trust, now)


def resign_vote(data: dict[str, Any], key: KeyFile) -> None:
    data["signatures"] = crypto.sign(
        key.suite,
        key.private_keys,
        crypto.message("attestation", key.suite, key.identity, data["body"]),
    )


def exercise(
    name: str,
    root: Path,
    trust: TrustBundle,
    request: SignedIntent,
    receipt: Receipt,
    database: Path,
) -> str:
    q, r, t = (copy.deepcopy(x.model_dump()) for x in (request, receipt, trust))
    now = int(time.time())
    vote = r["attestations"][0]
    algorithms = crypto.components(trust.policy.suite)
    try:
        if name in {"modified_action_payload", "altered_frozen_experiment"}:
            q["intent"]["parameters"]["experiment"]["shots"] += 1
        elif name == "modified_target":
            q["intent"]["target"] = "simulator:attacker"
        elif name == "modified_receipt_nonce":
            r["header"]["receipt_id"] = "f" * 32
        elif name == "wrong_public_key":
            t["verifiers"]["verifier-1"] = crypto.generate(trust.policy.suite)[1]
        elif name == "missing_required_signature":
            del vote["signatures"][algorithms[-1]]
        elif name == "algorithm_downgrade":
            q["intent"]["required_suite"] = (
                "ed25519-v1" if trust.policy.suite != "ed25519-v1" else "mldsa65-v1"
            )
        elif name == "expired_receipt":
            r["header"]["expires_at"] = now
        elif name == "future_receipt":
            r["header"]["issued_at"] = now + 10
        elif name == "future_intent":
            q["intent"]["created_at"] = now + 10
        elif name in {"receipt_replay", "reissued_intent_replay"}:
            executor = ProtectedExecutor(trust, load_key(root, "executor"), ReplayStore(database))
            executor.execute(canonical(request), canonical(receipt))
            if name == "reissued_intent_replay":
                r = issue(root, trust, request).model_dump()
            executor.execute(canonical(q), canonical(r))
        elif name in {"insufficient_quorum", "malicious_only_no_quorum"}:
            r["attestations"] = r["attestations"][:1]
        elif name == "duplicate_verifier":
            r["attestations"][1] = copy.deepcopy(vote)
        elif name == "unknown_verifier":
            vote["body"]["verifier_id"] = "attacker"
        elif name == "incorrect_policy_version":
            q["intent"]["policy"]["version"] += 1
        elif name == "malformed_duplicate_json":
            decode(b'{"intent":1,"intent":2}')
        elif name == "signature_substitution":
            vote["signatures"] = r["attestations"][1]["signatures"]
        elif name == "one_malicious_verifier":
            vote["body"]["predicates"]["circuit_well_formed"] = False
            resign_vote(vote, load_key(root, "verifier-1"))
        elif name == "two_honest_verifiers":
            r["attestations"] = r["attestations"][1:]
        elif name == "policy_changed_same_version":
            t["policy"]["max_qubits"] = 7
        elif name == "receipt_threshold_downgrade":
            r["header"]["quorum"] = 1
        elif name == "receipt_suite_downgrade":
            r["header"]["suite"] = (
                "ed25519-v1" if trust.policy.suite != "ed25519-v1" else "mldsa65-v1"
            )
        elif name == "evidence_mutation":
            vote["body"]["predicates"]["circuit_well_formed"] = False
        elif name == "missing_evidence":
            vote["body"]["predicates"] = {}
        elif name == "outer_disposition_mutation":
            r["disposition"] = "DENY"
        elif name in {"human_verify_not_approval", "deny_not_approval", "signed_stale_freeze"}:
            from .models import Intent

            if name == "human_verify_not_approval":
                spec = bell_experiment().model_copy(update={"shots": 3000})
                changed = freeze(spec, trust)
            else:
                raw = request.intent.model_dump()
                if name == "deny_not_approval":
                    raw["target"] = "simulator:disallowed"
                else:
                    raw["parameters"]["experiment"]["shots"] += 1
                changed = parse(Intent, canonical(raw))
            new_request = sign_intent(changed, load_key(root, "scientist"))
            q, r = new_request.model_dump(), issue(root, trust, new_request).model_dump()
        elif name == "unknown_not_approval":
            r["attestations"], r["disposition"] = [], "UNKNOWN"
        elif name == "error_not_approval":
            vote["body"]["disposition"] = "ERROR"
            resign_vote(vote, load_key(root, "verifier-1"))
        elif name == "shared_identity_key":
            t["verifiers"]["verifier-2"] = t["verifiers"]["verifier-1"].copy()
        elif name == "extra_signature_algorithm":
            vote["signatures"]["made-up"] = "AA=="
        elif name == "request_signature_missing":
            q["signatures"] = {}
        elif name == "cross_domain_signature":
            key = load_key(root, "verifier-1")
            vote["signatures"] = crypto.sign(
                key.suite,
                key.private_keys,
                crypto.message("result", key.suite, key.identity, vote["body"]),
            )
        elif name == "audience_swap":
            q["intent"]["audience"] = "other-executor"
        elif name == "extra_intent_field":
            q["intent"]["override"] = True
        elif name == "float_canonical_input":
            decode(b'{"shots":1.0}')
        elif name == "boolean_schema_version":
            q["intent"]["schema_version"] = True
        elif name == "result_tampering":
            executor = ProtectedExecutor(trust, load_key(root, "executor"), ReplayStore(database))
            result = executor.execute(canonical(request), canonical(receipt)).model_dump()
            result["body"]["counts"]["00"] += 1
            verify_result(canonical(result), canonical(request), canonical(receipt), trust)
        elif name == "noncanonical_base64":
            vote["signatures"][algorithms[0]] += "\n"
            # Test provider decoder directly; PGJ would also reject the control character.
            crypto.unbase64(vote["signatures"][algorithms[0]])
        elif name == "expired_intent":
            q["intent"]["expires_at"] = now
        elif name != "valid_authorization":
            raise AssertionError(f"Unimplemented corpus case: {name}")
        verify_receipt(canonical(q), canonical(r), parse(TrustBundle, canonical(t)), now)
        return "ALLOW"
    except GateError as exc:
        return exc.code


def run_corpus(output: Path, suite: Suite = "ed25519-mldsa65-v1") -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="proofgate-attacks-") as directory:
        base = Path(directory)
        root = base / "keys"
        trust, request, receipt = material(root, suite)
        for name, expected in CASES.items():
            actual = exercise(name, root, trust, request, receipt, base / f"{name}.sqlite")
            rows.append(
                {
                    "attack": name,
                    "expected": expected,
                    "actual": actual,
                    "passed": actual == expected,
                }
            )
    report = {
        "suite": suite,
        "cases": rows,
        "passed": sum(r["passed"] for r in rows),
        "total": len(rows),
        "generated_at": int(time.time()),
    }
    write(output, report)
    lines = [
        "# Adversarial corpus",
        "",
        f"Suite: `{suite}`. {report['passed']}/{len(rows)} passed.",
        "",
        "| Case | Expected | Observed | Result |",
        "|---|---|---|---|",
    ]
    lines += [
        f"| {r['attack']} | {r['expected']} | {r['actual']} | {'PASS' if r['passed'] else 'FAIL'} |"
        for r in rows
    ]
    output.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
