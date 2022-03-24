from consts import *
from deploy import deploy_initial_Chainflip_contracts
from shared_tests import *
from brownie import reverts, chain, web3
from brownie.test import given, strategy


@given(
    whitelist=strategy("address[]", unique=True),
)
def test_setCanValidateSig(a, KeyManager, Vault, StakeManager, FLIP, whitelist):

    cf = deploy_initial_Chainflip_contracts(a[0], KeyManager, Vault, StakeManager, FLIP)
    cf.keyManager.setCanValidateSig(whitelist)
    for addr in whitelist:
        assert cf.keyManager.canValidateSig(addr) == True

    assert cf.keyManager.getNumberWhitelistedAddresses() == len(whitelist)


def test_setCanValidateSig_rev_duplicate(a, KeyManager, Vault, StakeManager, FLIP):
    cf = deploy_initial_Chainflip_contracts(a[0], KeyManager, Vault, StakeManager, FLIP)
    with reverts(REV_MSG_DUPLICATE):
        cf.keyManager.setCanValidateSig(list(a) + list(a))


def test_setCanValidateSig_rev(a, cf):
    with reverts(REV_MSG_SET):
        cf.keyManager.setCanValidateSig(list(a))
