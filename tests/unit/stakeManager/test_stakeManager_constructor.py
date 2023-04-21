from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy


def test_constructor(cf):
    assert cf.stakeManager.getKeyManager() == cf.keyManager.address
    assert cf.stakeManager.getKeyManager() == cf.keyManager.address
    assert cf.stakeManager.getMinimumStake() == MIN_STAKE
    assert cf.flip.totalSupply() == INIT_SUPPLY
    assert cf.flip.balanceOf(cf.stakeManager) == STAKEMANAGER_INITIAL_BALANCE
    assert cf.stakeManager.getLastSupplyUpdateBlockNumber() == 0


# Tries to set the FLIP address. It should have been set at deployment.
@given(
    st_sender=strategy("address"),
    st_flip_address=strategy("address"),
)
def test_setFlip(cf, st_sender, st_flip_address):
    print("        REV_MSG_NZ_ADDR rule_setFlip", st_sender)
    with reverts(REV_MSG_NZ_ADDR):
        cf.stakeManager.setFlip(ZERO_ADDR, {"from": st_sender})

    print("        REV_MSG_FLIP_ADDRESS rule_setFlip", st_sender)
    with reverts(REV_MSG_FLIP_ADDRESS):
        cf.stakeManager.setFlip(st_flip_address, {"from": st_sender})
