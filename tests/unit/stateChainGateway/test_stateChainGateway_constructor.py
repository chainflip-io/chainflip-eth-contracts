from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy


def test_constructor(cf):
    assert cf.stateChainGateway.getKeyManager() == cf.keyManager.address
    assert cf.stateChainGateway.getKeyManager() == cf.keyManager.address
    assert cf.stateChainGateway.getMinimumFunding() == MIN_FUNDING
    assert cf.stateChainGateway.REDEMPTION_DELAY() == REDEMPTION_DELAY
    assert cf.flip.totalSupply() == INIT_SUPPLY
    assert cf.flip.balanceOf(cf.stateChainGateway) == GATEWAY_INITIAL_BALANCE
    assert cf.stateChainGateway.getLastSupplyUpdateBlockNumber() == 0


def test_constructor_nzUint(cf, StateChainGateway):
    with reverts(REV_MSG_NZ_UINT):
        StateChainGateway.deploy(NON_ZERO_ADDR, MIN_FUNDING, 0, {"from": cf.deployer})

    try:
        StateChainGateway.deploy(
            NON_ZERO_ADDR, MIN_FUNDING, 2**48, {"from": cf.deployer}
        )
    except:
        pass
    else:
        raise Exception("Should have reverted")

    StateChainGateway.deploy(
        NON_ZERO_ADDR, MIN_FUNDING, 2**48 - 1, {"from": cf.deployer}
    )


# Tries to set the FLIP address. It should have been set at deployment.
@given(
    st_sender=strategy("address"),
    st_flip_address=strategy("address"),
)
def test_setFlip(cf, st_sender, st_flip_address):
    print("        REV_MSG_NZ_ADDR rule_setFlip", st_sender)
    with reverts(REV_MSG_NZ_ADDR):
        cf.stateChainGateway.setFlip(ZERO_ADDR, {"from": st_sender})

    print("        REV_MSG_FLIP_ADDRESS rule_setFlip", st_sender)
    with reverts(REV_MSG_FLIP_ADDRESS):
        cf.stateChainGateway.setFlip(st_flip_address, {"from": st_sender})
