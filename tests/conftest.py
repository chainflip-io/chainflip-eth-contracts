import pytest
from consts import *



# Test isolation
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


# Deploy the contracts for repeated tests without having to redeploy each time

@pytest.fixture(scope="module")
def vault(a, Vault):
    vault = a[0].deploy(Vault, *AGG_SIGNER_1.getPubData(), *GOV_SIGNER_1.getPubData())
    return vault


@pytest.fixture(scope="module")
def token(a, Token):
    token = a[0].deploy(Token, "ShitCoin", "SC", 10**21)
    return token


@pytest.fixture(scope="module")
def schnorrSECP256K1(a, SchnorrSECP256K1):
    return a[0].deploy(SchnorrSECP256K1)
