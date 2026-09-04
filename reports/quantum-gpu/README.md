# Public protected GPU experiment evidence

Actual 24-qubit, 568-gate H/T/CX run through hybrid 3-of-3 authorization.
This directory contains only public keys, frozen input, signatures and result/provenance.
Private keys and replay storage remain in the ignored local demo directory.

```bash
python -m proofgate --root reports/quantum-gpu verify-result
```

Verification uses the signed historical execution time; it never authorizes new execution.
summary.json includes measured adapter metadata, including actual device=GPU.
The result signature binds the specification, receipt and counts, not the unsigned
timing/driver metadata in summary.json. Trust anchors must already be trusted by a
relying party; a self-contained bundle does not bootstrap trust.
