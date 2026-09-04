# Example configuration

`experiment.json` is a Bell-state specification accepted by schema v1. `policy.json`
is the default 2-of-3 policy without keys. `proofgate init` provisions a complete
`trust.json` with fresh requester, verifier and executor public keys and separate
plaintext private-key files. Do not reuse the public evidence keys for a deployment.

For a policy change, update the administrative trust bundle before issuing new receipts
and increment `policy.reference.version`. Policy contents are hashed, so even changing
limits without incrementing the version makes existing receipts fail. For 3-of-3,
use `proofgate --root <new-directory> init --quorum 3`.

No Docker orchestration is required: the coordinator runs three bounded, authenticated
stdio verifier processes concurrently. Only each node's own private key is loaded into
its process. Filesystem ownership is shared in this demo; it is not a credential sandbox.
