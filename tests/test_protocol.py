import time
from unittest.mock import patch

import pytest
from cryptography.exceptions import UnsupportedAlgorithm

from proofgate import crypto
from proofgate.attacks import issue, resign_vote
from proofgate.canonical import canonical, decode, parse
from proofgate.demo import quantum_demo
from proofgate.errors import GateError
from proofgate.local import bell_experiment, freeze, load_key, provision, sign_intent
from proofgate.models import Intent, TrustBundle
from proofgate.protocol import verify_receipt


@pytest.mark.parametrize("quorum", [2, 3])
def test_three_actual_verifier_processes(tmp_path, quorum):
    result = quantum_demo(tmp_path / "cluster", quorum=quorum)
    assert len({n["pid"] for n in result["nodes"]}) == 3
    assert result["disposition"] == "ALLOW"
    assert result["replay_after_restart"] == "REPLAY"


def test_three_of_three_requires_all(tmp_path):
    root = tmp_path / "cluster"
    trust = provision(root, quorum=3)
    request = sign_intent(freeze(bell_experiment(), trust), load_key(root, "scientist"))
    receipt = issue(root, trust, request).model_dump()
    receipt["attestations"].pop()
    with pytest.raises(GateError, match="DISPOSITION_MISMATCH"):
        verify_receipt(canonical(request), canonical(receipt), trust, int(time.time()))


def test_malicious_signer_approves_policy_denial(cluster):
    root, trust, request, _ = cluster
    intent = request.intent.model_dump()
    intent["target"] = "simulator:forbidden"
    request = sign_intent(parse(Intent, canonical(intent)), load_key(root, "scientist"))
    receipt = issue(root, trust, request).model_dump()
    receipt["attestations"][0]["body"]["disposition"] = "ALLOW"
    resign_vote(receipt["attestations"][0], load_key(root, "verifier-1"))
    with pytest.raises(GateError, match="DECISION_MISMATCH"):
        verify_receipt(canonical(request), canonical(receipt), trust, int(time.time()))


def test_coordinator_cannot_assemble_duplicates(cluster):
    from proofgate.protocol import assemble

    _, trust, request, receipt = cluster
    with pytest.raises(GateError, match="VERIFIER_DUPLICATE"):
        assemble(request, receipt.header, [receipt.attestations[0]] * 2, trust, int(time.time()))


def test_unavailable_provider_has_no_fallback():
    with patch.object(crypto, "PRIVATE", {"ml-dsa-65": None}):
        # Use a deliberately unavailable provider implementation with its documented exception.
        class Unavailable:
            @staticmethod
            def generate():
                raise UnsupportedAlgorithm("unavailable")

        crypto.PRIVATE["ml-dsa-65"] = Unavailable
        with pytest.raises(GateError, match="PROVIDER_UNAVAILABLE"):
            crypto.generate("mldsa65-v1")


@pytest.mark.parametrize("suite", ["unknown", "slhdsa-v1", "", "ed25519"])
def test_unknown_suite_rejected(suite):
    with pytest.raises(GateError, match="SUITE_UNSUPPORTED"):
        crypto.generate(suite)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"x":NaN}',
        b'{"x":Infinity}',
        b'{"x":1.0}',
        b'{"x":1e0}',
        b'{"x":-0}',
        b'{"x":9007199254740992}',
        b'{"x":1,"x":2}',
        b'{"x":"\\ud800"}',
        b'{"x":"\\u00e9"}',
        b'{"x":"\\n"}',
        b"\xff",
        b"{",
        b"[" * 40 + b"0" + b"]" * 40,
        b" " * 1_048_577,
    ],
    ids=lambda raw: f"bytes-{len(raw)}",
)
def test_malformed_canonical_inputs(raw):
    with pytest.raises(GateError):
        decode(raw)


def test_duplicate_key_alias_rejected():
    with pytest.raises(GateError, match="DUPLICATE_JSON_KEY"):
        decode(b'{"a":1,"\\u0061":2}')


def test_equivalent_transport_serialization(cluster):
    import json

    _, trust, request, receipt = cluster
    verify_receipt(
        json.dumps(request.model_dump(), indent=4).encode(),
        json.dumps(receipt.model_dump(), indent=2).encode(),
        trust,
        int(time.time()),
    )


def test_trust_bundle_cannot_rename_shared_component(cluster):
    _, trust, request, receipt = cluster
    data = trust.model_dump()
    data["verifiers"]["verifier-2"]["ml-dsa-65"] = data["verifiers"]["verifier-1"]["ml-dsa-65"]
    with pytest.raises(GateError, match="TRUST_DUPLICATE_KEY"):
        verify_receipt(
            canonical(request),
            canonical(receipt),
            parse(TrustBundle, canonical(data)),
            int(time.time()),
        )
