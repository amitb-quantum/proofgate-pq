"""The protected execution entry point: verify -> reserve durably -> side effect."""

import sqlite3
import time
from contextlib import closing
from pathlib import Path

from . import crypto
from .canonical import canonical, digest, parse
from .errors import GateError, require
from .models import AerPolicy, KeyFile, ResultBody, ResultRecord, SignedIntent, TrustBundle
from .protocol import trust_snapshot, verify_receipt
from .simulator import SimulatorAdapter, StatevectorSimulator


class ReplayStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        require(str(path) != ":memory:", "REPLAY_STORE_NOT_DURABLE")

    def reserve(self, receipt_id: str, intent_key: str, expires_at: int) -> None:
        try:
            with closing(sqlite3.connect(self.path, timeout=5)) as connection, connection:
                connection.execute("PRAGMA synchronous=FULL")
                connection.execute("""CREATE TABLE IF NOT EXISTS reservations (
                    receipt_id TEXT PRIMARY KEY, intent_key TEXT NOT NULL UNIQUE,
                    expires_at INTEGER NOT NULL)""")
                connection.execute("BEGIN IMMEDIATE")
                require(int(time.time()) < expires_at, "RECEIPT_EXPIRED")
                connection.execute(
                    "INSERT INTO reservations VALUES (?, ?, ?)",
                    (receipt_id, intent_key, expires_at),
                )
        except sqlite3.IntegrityError as exc:
            raise GateError("REPLAY") from exc
        except sqlite3.Error as exc:
            raise GateError("REPLAY_STORE_ERROR") from exc


class ProtectedExecutor:
    def __init__(
        self,
        trust: TrustBundle,
        key: KeyFile,
        store: ReplayStore,
        adapter: SimulatorAdapter | None = None,
    ) -> None:
        self._trust = trust_snapshot(trust)
        self._key = parse(KeyFile, canonical(key))
        require(
            key.identity == trust.executor_id and key.suite == trust.policy.suite,
            "EXECUTOR_KEY_MISMATCH",
        )
        # Validate the result signer before any side effect can occur.
        probe = crypto.message("result", key.suite, key.identity, {"probe": True})
        crypto.verify(
            key.suite, trust.executor_keys, crypto.sign(key.suite, key.private_keys, probe), probe
        )
        self._store = store
        if adapter is not None:
            self._adapter = adapter
        elif isinstance(self._trust.policy, AerPolicy):
            from .aer import AER_GPU, AerAdapter

            self._adapter = AerAdapter("GPU" if self._trust.policy.backend == AER_GPU else "CPU")
        else:
            self._adapter = StatevectorSimulator()

    def execute(self, request_data: bytes, receipt_data: bytes) -> ResultRecord:
        request, receipt = verify_receipt(request_data, receipt_data, self._trust, int(time.time()))
        intent = request.intent
        spec = intent.parameters.experiment
        require(self._adapter.revision == spec.backend, "BACKEND_MISMATCH")
        intent_key = digest(
            "replay",
            {"audience": intent.audience, "subject": intent.subject, "nonce": intent.nonce},
        )
        self._store.reserve(receipt.header.receipt_id, intent_key, receipt.header.expires_at)
        try:
            executed_at = int(time.time())
            # A second real-clock check after a potentially blocking SQLite reservation.
            require(executed_at < receipt.header.expires_at, "RECEIPT_EXPIRED")
            counts = self._adapter.run(spec)
            body = ResultBody(
                schema_version=1,
                executor_id=self._trust.executor_id,
                suite=self._trust.policy.suite,
                audience=intent.audience,
                action_digest=digest("intent", intent),
                frozen_digest=intent.parameters.frozen_digest,
                receipt_digest=digest("receipt", receipt),
                receipt_id=receipt.header.receipt_id,
                backend=spec.backend,
                executed_at=executed_at,
                counts=counts,
            )
            _check_counts(body, request)
            return ResultRecord(
                body=body,
                signatures=crypto.sign(
                    self._key.suite,
                    self._key.private_keys,
                    crypto.message("result", self._key.suite, self._key.identity, body),
                ),
            )
        except GateError:
            raise
        except Exception as exc:
            # Reservation deliberately remains spent even on adapter/signing failure.
            raise GateError("EXECUTION_ERROR") from exc


def _check_counts(body: ResultBody, request: SignedIntent) -> None:
    spec = request.intent.parameters.experiment
    require(bool(body.counts), "RESULT_COUNTS_INVALID")
    require(
        all(
            len(k) == spec.qubits and set(k) <= {"0", "1"} and type(v) is int and v > 0
            for k, v in body.counts.items()
        ),
        "RESULT_COUNTS_INVALID",
    )
    require(sum(body.counts.values()) == spec.shots, "RESULT_COUNTS_INVALID")


def verify_result(
    result_data: bytes, request_data: bytes, receipt_data: bytes, trust: TrustBundle
) -> ResultRecord:
    """Historical provenance verification at claimed execution time; no new authorization."""
    result = parse(ResultRecord, result_data)
    body = result.body
    trusted = trust_snapshot(trust)
    require(body.executor_id == trusted.executor_id, "EXECUTOR_UNKNOWN")
    require(body.suite == trusted.policy.suite, "SUITE_MISMATCH")
    crypto.verify(
        body.suite,
        trusted.executor_keys,
        result.signatures,
        crypto.message("result", body.suite, body.executor_id, body),
    )
    request, receipt = verify_receipt(request_data, receipt_data, trusted, body.executed_at)
    _check_counts(body, request)
    require(body.action_digest == digest("intent", request.intent), "RESULT_ACTION_MISMATCH")
    require(body.frozen_digest == request.intent.parameters.frozen_digest, "RESULT_SPEC_MISMATCH")
    require(body.receipt_digest == digest("receipt", receipt), "RESULT_RECEIPT_MISMATCH")
    require(body.receipt_id == receipt.header.receipt_id, "RESULT_RECEIPT_MISMATCH")
    require(body.backend == request.intent.parameters.experiment.backend, "BACKEND_MISMATCH")
    require(body.audience == trusted.policy.audience, "AUDIENCE_MISMATCH")
    return result
