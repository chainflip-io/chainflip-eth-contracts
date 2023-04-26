from consts import *
from brownie.test import given, strategy
from brownie import reverts, chain
from utils import *
from shared_tests import *
from deploy import deploy_new_stateChainGateway


def test_updateIssuer_rev_nzAddr(cf):
    with reverts(REV_MSG_NZ_ADDR):
        signed_call_cf(
            cf,
            cf.stateChainGateway.updateFlipIssuer,
            ZERO_ADDR,
            sender=cf.BOB,
        )


def test_updateIssuer(
    cf,
    KeyManager,
    StateChainGateway,
    FLIP,
    DeployerStateChainGateway,
):

    (_, new_stateChainGateway) = deploy_new_stateChainGateway(
        cf.deployer,
        KeyManager,
        StateChainGateway,
        FLIP,
        DeployerStateChainGateway,
        cf.keyManager.address,
        cf.flip.address,
        MIN_FUNDING,
    )

    tx = signed_call_cf(
        cf,
        cf.stateChainGateway.updateFlipIssuer,
        new_stateChainGateway.address,
        sender=cf.BOB,
    )

    assert tx.events["IssuerUpdated"].values() == [
        cf.stateChainGateway.address,
        new_stateChainGateway.address,
    ]

    # Check that the new stateChainGateway can update the supply
    iniBals.scg = cf.flip.balanceOf(new_stateChainGateway.address)
    tx = signed_call_cf(
        cf,
        new_stateChainGateway.updateFlipSupply,
        INIT_SUPPLY + 1,
        1,
        sender=cf.ALICE,
    )
    assert tx.events["FlipSupplyUpdated"].values() == [INIT_SUPPLY, INIT_SUPPLY + 1, 1]
    assert tx.events["Transfer"].values() == [
        ZERO_ADDR,
        new_stateChainGateway.address,
        1,
    ]
    assert cf.flip.balanceOf(new_stateChainGateway.address) == iniBals.scg + 1
