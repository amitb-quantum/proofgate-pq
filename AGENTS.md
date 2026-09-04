# ProofGate-PQ execution environment

Primary project: /home/manager/proofgate-pq (~/proofgate-pq), WSL Ubuntu-26.04.
Dedicated Conda environment: proofgate-pq, existing ~/miniforge3.
Activate: source ~/miniforge3/etc/profile.d/conda.sh && conda activate proofgate-pq.
Python 3.12 is deliberate: the existing protocol and provider wheels were validated
on 3.12. System Python 3.14.4 and Conda base Python 3.13.13 are not project interpreters.

No global project packages, unrelated environment updates, driver replacement or host
CUDA installs. CUDA wheels belong only to proofgate-pq. Keep source, scripts, reports,
schemas and configuration under this directory. The earlier Windows checkout is a
preserved historical snapshot; this Linux tree is authoritative. No private-key sync,
paid cloud/QPU use or external publishing.

Read environment/README.md and docs/gpu-design.md before environment/GPU changes.
Preserve v1 semantics. Device/backend is signed; no GPU-to-CPU fallback.
Only ProtectedExecutor.execute admits protected runs. Direct backend benchmarks must
be labeled computation measurements rather than authorized executions.
Run pytest, ruff check/format and mypy. GPU integration tests are opt-in with
PROOFGATE_GPU_TESTS=1 and must actually execute on GPU when enabled.
Record raw samples, hardware/runtime metadata, workload sizes, warmups, trials and
synchronization. Separate initialization, warmed execution and transfers. Never infer
signature/gateway acceleration from vectorized predicate prefilter timings.
