from consts import *
from deploy import deploy_initial_Chainflip_contracts
from shared_tests import *
from brownie import reverts, chain, web3
from brownie.test import given, strategy


@given(
    whitelist=strategy("address[]", unique=True),
)
def test_setCanConsumeNonce(a, KeyManager, Vault, StakeManager, FLIP, whitelist):

    cf = deploy_initial_Chainflip_contracts(a[0], KeyManager, Vault, StakeManager, FLIP)
    whitelist = whitelist + [cf.keyManager]
    cf.keyManager.setCanConsumeNonce(whitelist)
    for addr in whitelist:
        assert cf.keyManager.canConsumeNonce(addr) == True

    assert cf.keyManager.getNumberWhitelistedAddresses() == len(whitelist)


def test_setCanConsumeNonce_rev_duplicate(a, KeyManager, Vault, StakeManager, FLIP):
    cf = deploy_initial_Chainflip_contracts(a[0], KeyManager, Vault, StakeManager, FLIP)
    with reverts(REV_MSG_DUPLICATE):
        cf.keyManager.setCanConsumeNonce(list(a) + list(a))


def test_setCanConsumeNonce_rev(a, cf):
    with reverts(REV_MSG_SET):
        cf.keyManager.setCanConsumeNonce(list(a))
