import pytest
from tradevision_d6 import D6Engine, ProofVerifier
from tradevision_d6.demo import DEMO_KEY, DEMO_KEY_ID, sample_request


@pytest.fixture
def request_base():
    return sample_request()


@pytest.fixture
def proven():
    return sample_request(with_proof=True)


@pytest.fixture
def engine():
    return D6Engine(ProofVerifier({DEMO_KEY_ID: DEMO_KEY}))
