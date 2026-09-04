"""Local provisioning and three independent OS verifier processes over bounded stdio."""

import os
import secrets
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import crypto
from .canonical import canonical, decode, digest, parse, read, write
from .errors import GateError, require
from .models import (
    AerExperiment,
    Attestation,
    Context,
    Experiment,
    Gate,
    Intent,
    KeyFile,
    NodeRequest,
    Parameters,
    Policy,
    PolicyRef,
    Receipt,
    SignedIntent,
    Suite,
    TrustBundle,
)
from .protocol import assemble, new_header, trust_snapshot


def provision(root: Path, suite: Suite = "ed25519-mldsa65-v1", quorum: int = 2) -> TrustBundle:
    require(not root.exists(), "WORKSPACE_EXISTS")
    require(quorum in (2, 3), "TRUST_QUORUM")
    root.mkdir(parents=True, mode=0o700)
    identities = ["verifier-1", "verifier-2", "verifier-3", "scientist", "executor"]
    public = {}
    for identity in identities:
        private, public[identity] = crypto.generate(suite)
        path = root / f"{identity}-private.json"
        write(path, KeyFile(schema_version=1, identity=identity, suite=suite, private_keys=private))
        if os.name != "nt":
            path.chmod(0o600)
    policy = Policy(
        schema_version=1,
        reference=PolicyRef(id="quantum-local", version=1),
        suite=suite,
        audience="lab-executor",
        target="simulator:local",
        environment="local",
        project="bell-study",
        subjects=["scientist"],
        verifier_ids=identities[:3],
        quorum=quorum,
        max_qubits=8,
        max_shots=4096,
        human_above_shots=2048,
        max_intent_ttl=600,
        receipt_ttl=120,
    )
    trust = TrustBundle(
        schema_version=1,
        policy=policy,
        verifiers={i: public[i] for i in identities[:3]},
        requesters={"scientist": public["scientist"]},
        executor_id="executor",
        executor_keys=public["executor"],
    )
    trust_snapshot(trust)
    write(root / "trust.json", trust)
    write(root / "experiment.json", bell_experiment())
    return trust


def bell_experiment() -> Experiment:
    return Experiment(
        schema_version=1,
        backend="builtin-statevector-v1",
        qubits=2,
        gates=[Gate(op="H", qubits=[0]), Gate(op="CX", qubits=[0, 1])],
        shots=1024,
        seed=7,
    )


def freeze(spec: Experiment | AerExperiment, trust: TrustBundle, now: int | None = None) -> Intent:
    now = int(time.time()) if now is None else now
    return Intent(
        schema_version=1,
        action_type="quantum.run",
        subject="scientist",
        target=trust.policy.target,
        audience=trust.policy.audience,
        parameters=Parameters(experiment=spec, frozen_digest=digest("experiment", spec)),
        context=Context(environment=trust.policy.environment, project=trust.policy.project),
        nonce=secrets.token_hex(16),
        created_at=now,
        expires_at=now + min(300, trust.policy.max_intent_ttl),
        policy=trust.policy.reference,
        required_suite=trust.policy.suite,
    )


def sign_intent(intent: Intent, key: KeyFile) -> SignedIntent:
    require(
        key.identity == intent.subject and key.suite == intent.required_suite,
        "REQUESTER_KEY_MISMATCH",
    )
    return SignedIntent(
        intent=intent,
        signatures=crypto.sign(
            key.suite, key.private_keys, crypto.message("intent", key.suite, key.identity, intent)
        ),
    )


def load_trust(root: Path) -> TrustBundle:
    return trust_snapshot(parse(TrustBundle, read(root / "trust.json")))


def load_key(root: Path, identity: str) -> KeyFile:
    # Only callers using known identity labels should use this local convenience function.
    require(
        identity in {"scientist", "executor", "verifier-1", "verifier-2", "verifier-3"},
        "IDENTITY_UNKNOWN",
    )
    return parse(KeyFile, read(root / f"{identity}-private.json"))


def authorize_processes(
    root: Path, request: SignedIntent
) -> tuple[Receipt, list[dict[str, int | str]]]:
    trust = load_trust(root)
    header = new_header(request, trust, int(time.time()))
    packet = canonical(NodeRequest(request=request, header=header))

    def call(identity: str) -> tuple[Attestation, dict[str, int | str]]:
        try:
            process = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "proofgate.node",
                    "--trust",
                    str(root / "trust.json"),
                    "--key",
                    str(root / f"{identity}-private.json"),
                ],
                input=packet,
                capture_output=True,
                timeout=20,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise GateError("VERIFIER_UNAVAILABLE") from exc
        require(process.returncode == 0, "VERIFIER_ERROR")
        response = decode(process.stdout)
        require(type(response) is dict and set(response) == {"pid", "attestation"}, "NODE_RESPONSE")
        require(type(response["pid"]) is int, "NODE_RESPONSE")
        attestation = parse(Attestation, canonical(response["attestation"]))
        require(attestation.body.verifier_id == identity, "VERIFIER_IDENTITY_MISMATCH")
        return attestation, {"identity": identity, "pid": response["pid"]}

    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(pool.map(call, trust.policy.verifier_ids))
    receipt = assemble(request, header, [r[0] for r in responses], trust, int(time.time()))
    return receipt, [r[1] for r in responses]
