import pytest
from consts import *



# Test isolation
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


# Deploy the contract for repeated tests without having to redeploy each time

@pytest.fixture(scope="module")
def vault(a, Vault):
    vault = a[0].deploy(Vault, *AGG_SIGNER_1.getPubData(), *AGG_SIGNER_1.getPubData())
    return vault

@pytest.fixture(scope="module")
def token(a, ERC20):
    token = a[0].deploy(ERC20, "ShitCoin", "SC", 10**21)
    return token



