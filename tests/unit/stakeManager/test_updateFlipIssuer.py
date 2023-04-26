from consts import *
from brownie.test import given, strategy
from brownie import reverts, chain
from utils import *
from shared_tests import *
from deploy import deploy_new_stakeManager


def test_updateIssuer_rev_nzAddr(cf):
    with reverts(REV_MSG_NZ_ADDR):
        signed_call_cf(
            cf,
            cf.stakeManager.updateFlipIssuer,
            ZERO_ADDR,
            sender=cf.BOB,
        )


def test_updateIssuer(
    cf,
    KeyManager,
    StakeManager,
    FLIP,
    DeployerStakeManager,
):

    (_, new_stakeManager) = deploy_new_stakeManager(
        cf.deployer,
        KeyManager,
        StakeManager,
        FLIP,
        DeployerStakeManager,
        cf.keyManager.address,
        cf.flip.address,
        MIN_STAKE,
    )

    tx = signed_call_cf(
        cf,
        cf.stakeManager.updateFlipIssuer,
        new_stakeManager.address,
        sender=cf.BOB,
    )

    assert tx.events["IssuerUpdated"].values() == [
        cf.stakeManager.address,
        new_stakeManager.address,
    ]

    # Check that the new stakeManager can update the supply
    iniBals_sm = cf.flip.balanceOf(new_stakeManager.address)
    tx = signed_call_cf(
        cf,
        new_stakeManager.updateFlipSupply,
        INIT_SUPPLY + 1,
        1,
        sender=cf.ALICE,
    )
    assert tx.events["FlipSupplyUpdated"].values() == [INIT_SUPPLY, INIT_SUPPLY + 1, 1]
    assert tx.events["Transfer"].values() == [ZERO_ADDR, new_stakeManager.address, 1]
    assert cf.flip.balanceOf(new_stakeManager.address) == iniBals_sm + 1
