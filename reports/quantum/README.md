# Public provenance evidence

These artifacts come from the recorded 3-of-3 hybrid demo. They contain **public keys
only**, a frozen experiment/intent, requester signatures, verifier receipt, result
attestation and execution summary. The demo's private keys and replay database are
excluded. These are historical evidence; their short authorization window has expired.

From the repository root, with the environment activated:

```powershell
python -m proofgate --root reports/quantum verify-result
```

This verifies the signed result and authorization at the signed execution time. It does
not consult a live replay store, prove wall-clock time, establish trusted key distribution
or authorize a new execution. Anyone can create a different self-contained bundle with
their own keys; only keys already trusted by a relying party establish their identity.
