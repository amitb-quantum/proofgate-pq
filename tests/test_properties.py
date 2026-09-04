import copy
import time

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from proofgate import crypto
from proofgate.canonical import canonical, decode, digest
from proofgate.errors import GateError
from proofgate.protocol import verify_receipt


def leaves(value, prefix=()):
    if isinstance(value, dict):
        return [p for key, child in value.items() for p in leaves(child, (*prefix, key))]
    if isinstance(value, list):
        return [p for index, child in enumerate(value) for p in leaves(child, (*prefix, index))]
    return [prefix]


def mutate(value, path, salt=1):
    cursor = value
    for key in path[:-1]:
        cursor = cursor[key]
    old = cursor[path[-1]]
    if type(old) is bool:
        new = not old
    elif type(old) is int:
        new = old + salt
    else:
        new = old + str(salt)
    cursor[path[-1]] = new


def test_every_bound_intent_leaf(cluster):
    _, trust, request, receipt = cluster
    paths = leaves(request.intent.model_dump())
    assert len(paths) == 24
    for path in paths:
        changed = request.model_dump()
        mutate(changed["intent"], path)
        with pytest.raises(GateError):
            verify_receipt(canonical(changed), canonical(receipt), trust, int(time.time()))


def test_every_bound_attestation_leaf(cluster):
    _, trust, request, receipt = cluster
    for path in leaves(receipt.attestations[0].body.model_dump()):
        changed = receipt.model_dump()
        mutate(changed["attestations"][0]["body"], path)
        with pytest.raises(GateError):
            verify_receipt(canonical(request), canonical(changed), trust, int(time.time()))


@settings(
    max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    index=st.integers(min_value=0, max_value=1000), salt=st.integers(min_value=1, max_value=10000)
)
def test_generated_bound_mutations(cluster, index, salt):
    _, trust, request, receipt = cluster
    changed = request.model_dump()
    paths = leaves(changed["intent"])
    mutate(changed["intent"], paths[index % len(paths)], salt)
    with pytest.raises(GateError):
        verify_receipt(canonical(changed), canonical(receipt), trust, int(time.time()))


@settings(
    max_examples=60, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(permutation=st.permutations([0, 1, 2]))
def test_quorum_permutation_does_not_change_approval(cluster, permutation):
    _, trust, request, receipt = cluster
    data = receipt.model_dump()
    data["attestations"] = [data["attestations"][i] for i in permutation]
    verify_receipt(canonical(request), canonical(data), trust, int(time.time()))


@settings(
    max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(identity=st.integers(min_value=0, max_value=2), count=st.integers(min_value=2, max_value=16))
def test_repeating_identity_never_adds_quorum(cluster, identity, count):
    _, trust, request, receipt = cluster
    data = receipt.model_dump()
    data["attestations"] = [copy.deepcopy(data["attestations"][identity]) for _ in range(count)]
    with pytest.raises(GateError, match="VERIFIER_DUPLICATE"):
        verify_receipt(canonical(request), canonical(data), trust, int(time.time()))


json_values = st.recursive(
    st.none()
    | st.booleans()
    | st.integers(-(2**53 - 1), 2**53 - 1)
    | st.text(alphabet=st.characters(min_codepoint=32, max_codepoint=126), max_size=30),
    lambda child: (
        st.lists(child, max_size=4)
        | st.dictionaries(st.text(alphabet="abcxyz", max_size=8), child, max_size=4)
    ),
    max_leaves=20,
)


@given(value=json_values)
def test_canonical_roundtrip_and_digest_stability(value):
    encoded = canonical(value)
    assert canonical(decode(encoded)) == encoded
    assert digest("test", value) == digest("test", decode(encoded))


@given(values=st.dictionaries(st.text(alphabet="abcd", max_size=8), st.integers(-999, 999)))
def test_object_key_order_invariance(values):
    assert canonical(values) == canonical(dict(reversed(list(values.items()))))


@settings(
    max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(index=st.integers(0, 3308), mask=st.integers(1, 255))
def test_pq_signature_bit_mutation(cluster, index, mask):
    _, trust, request, receipt = cluster
    data = receipt.model_dump()
    signatures = data["attestations"][0]["signatures"]
    sig = bytearray(crypto.unbase64(signatures["ml-dsa-65"]))
    sig[index] ^= mask
    signatures["ml-dsa-65"] = crypto.encode(sig)
    with pytest.raises(GateError, match="SIGNATURE_INVALID"):
        verify_receipt(canonical(request), canonical(data), trust, int(time.time()))
