from consts import *
from deploy import deploy_initial_Chainflip_contracts
from shared_tests import *
from brownie import reverts, chain, web3
from brownie.test import given, strategy


@given(
    st_whitelist=strategy("address[]", unique=True),
)
def test_setCanConsumeKeyNonce(a, KeyManager, Vault, StakeManager, FLIP, st_whitelist):

    cf = deploy_initial_Chainflip_contracts(a[9], KeyManager, Vault, StakeManager, FLIP)
    tx = cf.keyManager.setCanConsumeKeyNonce(st_whitelist)
    assert tx.events["AggKeyNonceConsumersSet"][0].values()[0] == st_whitelist

    for addr in st_whitelist:
        assert cf.keyManager.canConsumeKeyNonce(addr) == True

    assert cf.keyManager.getNumberWhitelistedAddresses() == len(st_whitelist)


@given(
    st_sender=strategy("address"),
    st_whitelist=strategy("address[]", unique=True),
)
def test_setCanConsumeKeyNonce_rev_sender(
    a, KeyManager, Vault, StakeManager, FLIP, st_whitelist, st_sender
):

    cf = deploy_initial_Chainflip_contracts(a[9], KeyManager, Vault, StakeManager, FLIP)

    if st_sender != cf.deployer:
        with reverts(REV_MSG_KEYMANAGER_NOT_DEPLOYER):
            cf.keyManager.setCanConsumeKeyNonce(st_whitelist, {"from": st_sender})
    else:
        cf.keyManager.setCanConsumeKeyNonce(st_whitelist, {"from": st_sender})


def test_setCanConsumeKeyNonce_rev_duplicate(a, KeyManager, Vault, StakeManager, FLIP):
    cf = deploy_initial_Chainflip_contracts(a[9], KeyManager, Vault, StakeManager, FLIP)
    with reverts(REV_MSG_DUPLICATE):
        cf.keyManager.setCanConsumeKeyNonce(list(a) + list(a))


def test_setCanConsumeKeyNonce_rev(a, cf):
    with reverts(REV_MSG_SET):
        cf.keyManager.setCanConsumeKeyNonce(list(a))
