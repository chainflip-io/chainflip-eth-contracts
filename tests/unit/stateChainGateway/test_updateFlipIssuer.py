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


def test_updateIssuer_rev_eoa(cf):
    with reverts("Transaction reverted without a reason string"):
        signed_call_cf(
            cf,
            cf.stateChainGateway.updateFlipIssuer,
            cf.ALICE,
            sender=cf.BOB,
        )


def test_updateIssuer_rev_nonIssuer(cf):
    with reverts("Transaction reverted without a reason string"):
        signed_call_cf(
            cf,
            cf.stateChainGateway.updateFlipIssuer,
            cf.vault.address,
            sender=cf.BOB,
        )


def test_updateIssuer_rev_notFLIP(
    cf, KeyManager, StateChainGateway, DeployerStateChainGateway, FLIP
):
    # Deploy a mock FLIP
    flip_mock = cf.deployer.deploy(
        FLIP,
        INIT_SUPPLY,
        cf.numGenesisValidators,
        cf.genesisStake,
        cf.deployer,
        cf.deployer,
        cf.deployer,
    )

    (_, newStateChainGateway) = deploy_new_stateChainGateway(
        cf.deployer,
        KeyManager,
        StateChainGateway,
        FLIP,
        DeployerStateChainGateway,
        cf.keyManager.address,
        flip_mock.address,
        MIN_FUNDING,
    )

    with reverts(REV_MSG_NOT_FLIP):
        signed_call_cf(
            cf,
            cf.stateChainGateway.updateFlipIssuer,
            newStateChainGateway,
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
    iniBals_scg = cf.flip.balanceOf(new_stateChainGateway.address)
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
    assert cf.flip.balanceOf(new_stateChainGateway.address) == iniBals_scg + 1


def test_updateIssuer_rev_suspended(cf):
    cf.stateChainGateway.suspend({"from": cf.GOVERNOR})

    with reverts(REV_MSG_GOV_SUSPENDED):
        signed_call_cf(
            cf,
            cf.stateChainGateway.updateFlipIssuer,
            NON_ZERO_ADDR,
            sender=cf.BOB,
        )
