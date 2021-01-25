import pytest
from consts import *



# Test isolation
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


# Deploy the contracts for repeated tests without having to redeploy each time

def deploy_initial_ChainFlip_contracts(a, KeyManager, Vault, StakeManager):
    class Context:
        pass

    cf = Context()
    cf.keyManager = a[0].deploy(KeyManager, AGG_SIGNER_1.getPubData(), GOV_SIGNER_1.getPubData())
    cf.vault = a[0].deploy(Vault, cf.keyManager.address)
    cf.stakeManager = a[0].deploy(StakeManager, cf.keyManager.address, EMISSION_PER_SEC, MIN_STAKE)

    return cf


@pytest.fixture(scope="module")
def cf(a, KeyManager, Vault, StakeManager):
    return deploy_initial_ChainFlip_contracts(a, KeyManager, Vault, StakeManager)


@pytest.fixture(scope="module")
def token(a, Token):
    return a[0].deploy(Token, "ShitCoin", "SC", 10**21)
