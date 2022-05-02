from consts import *
from deploy import deploy_initial_Chainflip_contracts
from shared_tests import *
from brownie import reverts, chain, web3
from brownie.test import given, strategy


@given(
    whitelist=strategy("address[]", unique=True),
)
def test_setCanConsumeKeyNonce(a, KeyManager, Vault, StakeManager, FLIP, whitelist):

    cf = deploy_initial_Chainflip_contracts(a[0], KeyManager, Vault, StakeManager, FLIP)
    whitelist = whitelist + [cf.keyManager]
    cf.keyManager.setCanConsumeKeyNonce(whitelist)
    for addr in whitelist:
        assert cf.keyManager.canConsumeKeyNonce(addr) == True

    assert cf.keyManager.getNumberWhitelistedAddresses() == len(whitelist)


def test_setCanConsumeKeyNonce_rev_duplicate(a, KeyManager, Vault, StakeManager, FLIP):
    cf = deploy_initial_Chainflip_contracts(a[0], KeyManager, Vault, StakeManager, FLIP)
    with reverts(REV_MSG_DUPLICATE):
        cf.keyManager.setCanConsumeKeyNonce(list(a) + list(a))


def test_setCanConsumeKeyNonce_rev(a, cf):
    with reverts(REV_MSG_SET):
        cf.keyManager.setCanConsumeKeyNonce(list(a))
