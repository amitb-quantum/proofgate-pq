# GPU extension design (before implementation)

Preserve the signed v1 circuit: H/X/Z/CX, at most 8 qubits, built-in CPU backend.
Introduce a version-2 frozen experiment with explicit Aer CPU or Aer GPU backend,
up to 26 qubits, 2048 H/X/Z/CX/T gates and 4096 shots. T enables non-Clifford
workloads; merely scaling Bell/GHZ circuits would overlook efficient CPU stabilizers.
A version-2 policy pins the exact backend and limits. Backend device is signed.
Changing GPU to CPU requires fresh authorization; unavailable GPU fails closed.
Simulation uses maintained Qiskit Aer, never hand-written CUDA kernels.

The protected executor keeps its receipt validation and durable reservation boundary.
Result provenance binds the complete specification and exact backend identity.
The optional adapter checks GPU availability; no fallback. CPU/GPU provider settings
(fixed double precision, fixed thread count, statevector method and fusion setting)
are part of the backend revision contract rather than unsigned caller options.

Benchmarks compare the same Aer statevector circuits on CPU/GPU, verify provider
device metadata, separate first-call from warmed trials, alternate device order and
wait for completion. Small Bell and larger non-Clifford circuits measure overhead
and useful statevector workloads. This does not establish the fastest algorithm
for every circuit, so report a CPU stabilizer baseline for the Bell workload.

CuPy/NumPy compare vectorized resource-predicate prefiltering and statistical reductions.
These experimental batch computations do not replace parsing, signatures, quorum or
executor policy. Include transfers and synchronization in end-to-end measurements;
report resident-kernel time separately. Real high-volume signed admission tests remain CPU.
PyCA exposes no GPU signature API here; make no GPU signature acceleration claim.
SHA-384 stays hashlib/OpenSSL; no suitable reviewed GPU hashing integration is established.

Compatibility observation: Aer GPU 0.15.1 failed to import with Qiskit 2.5.2
(convert_to_target missing). Pin Qiskit 1.4.6: actual CPU and RTX 5090 GPU smoke runs
succeeded. CuPy 14.2.0 with environment-local CUDA 12.9 also computed successfully.
This older Aer GPU wheel is a prototype dependency limitation, not a reason to modify
the host driver. Its metadata reports cuStateVec_enable=false: use the actual Aer
CUDA/Thrust path and do not claim cuStateVec acceleration.
