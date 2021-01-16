import pytest
from consts import *



# Test isolation
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


# Deploy the contracts for repeated tests without having to redeploy each time

def deploy_initial_ChainFlip_contracts(a, KeyManager, Vault):
    class Context:
        pass

    cf = Context()

    cf.keyManager = a[0].deploy(KeyManager, AGG_SIGNER_1.getPubData(), GOV_SIGNER_1.getPubData())
    cf.vault = a[0].deploy(Vault, cf.keyManager.address)

    return cf


@pytest.fixture(scope="module")
def cf(a, KeyManager, Vault):
    return deploy_initial_ChainFlip_contracts(a, KeyManager, Vault)


@pytest.fixture(scope="module")
def token(a, Token):
    return a[0].deploy(Token, "ShitCoin", "SC", 10**21)
