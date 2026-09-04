"""Standalone verifier: only its private key and public trust configuration are loaded."""

import argparse
import os
import sys
import time
from pathlib import Path

from .canonical import MAX_BYTES, canonical, parse, read
from .errors import GateError
from .models import KeyFile, NodeRequest, TrustBundle
from .protocol import attest, trust_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trust", type=Path, required=True)
    parser.add_argument("--key", type=Path, required=True)
    args = parser.parse_args()
    try:
        trust = trust_snapshot(parse(TrustBundle, read(args.trust)))
        key = parse(KeyFile, read(args.key))
        packet = parse(NodeRequest, sys.stdin.buffer.read(MAX_BYTES + 1))
        result = attest(packet.request, packet.header, trust, key, int(time.time()))
        sys.stdout.buffer.write(canonical({"pid": os.getpid(), "attestation": result.model_dump()}))
        return 0
    except GateError as exc:
        sys.stderr.write(exc.code + "\n")
        return 2
    except Exception:
        sys.stderr.write("VERIFIER_ERROR\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
