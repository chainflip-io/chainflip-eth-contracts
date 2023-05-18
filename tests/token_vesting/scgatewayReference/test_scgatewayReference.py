from consts import *
from brownie import reverts, chain
from brownie.test import given, strategy
from shared_tests_tokenVesting import *


def test_reference_constructor(addrs, cf, SCGatewayReference):
    with reverts(REV_MSG_NZ_ADDR):
        addrs.DEPLOYER.deploy(SCGatewayReference, ZERO_ADDR, cf.stateChainGateway)

    with reverts(REV_MSG_NZ_ADDR):
        addrs.DEPLOYER.deploy(SCGatewayReference, NON_ZERO_ADDR, ZERO_ADDR)

    scGatewayReference = addrs.DEPLOYER.deploy(
        SCGatewayReference, addrs.DEPLOYER, NON_ZERO_ADDR
    )
    assert scGatewayReference.getGovernor() == addrs.DEPLOYER
    assert scGatewayReference.getStateChainGateway() == NON_ZERO_ADDR


def test_reference_updateGovernor(addrs, scGatewayReference):
    with reverts(REV_MSG_SCGREF_REV_GOV):
        scGatewayReference.updateGovernor(NON_ZERO_ADDR, {"from": addrs.INVESTOR})

    with reverts(REV_MSG_NZ_ADDR):
        scGatewayReference.updateGovernor(ZERO_ADDR, {"from": addrs.DEPLOYER})

    assert scGatewayReference.getGovernor() == addrs.DEPLOYER
    tx = scGatewayReference.updateGovernor(NON_ZERO_ADDR, {"from": addrs.DEPLOYER})
    assert tx.events["GovernorUpdated"][0].values() == [addrs.DEPLOYER, NON_ZERO_ADDR]
    assert scGatewayReference.getGovernor() == NON_ZERO_ADDR


def test_reference_updateReference(addrs, cf, scGatewayReference):
    with reverts(REV_MSG_SCGREF_REV_GOV):
        scGatewayReference.updateStateChainGateway(
            NON_ZERO_ADDR, {"from": addrs.INVESTOR}
        )

    with reverts(REV_MSG_NZ_ADDR):
        scGatewayReference.updateStateChainGateway(ZERO_ADDR, {"from": addrs.DEPLOYER})

    assert scGatewayReference.getStateChainGateway() == cf.stateChainGateway
    tx = scGatewayReference.updateStateChainGateway(
        NON_ZERO_ADDR, {"from": addrs.DEPLOYER}
    )
    assert tx.events["StateChainGatewayUpdated"][0].values() == [
        cf.stateChainGateway,
        NON_ZERO_ADDR,
    ]
    assert scGatewayReference.getStateChainGateway() == NON_ZERO_ADDR


def test_reference_release(addrs, cf, tokenVestingStaking, scGatewayReference):
    tv, _, _, _ = tokenVestingStaking

    assert cf.flip.balanceOf(addrs.INVESTOR) == 0

    tv.fundStateChainAccount(JUNK_INT, MAX_TEST_FUND, {"from": addrs.INVESTOR})

    chain.sleep(YEAR + QUARTER_YEAR)

    # Update the refernce to a wrong contract
    scGatewayReference.updateStateChainGateway(NON_ZERO_ADDR, {"from": addrs.DEPLOYER})

    # Mimic a return of funds from the state chain
    cf.flip.transfer(tv, MAX_TEST_FUND, {"from": addrs.DEPLOYER})

    assert cf.flip.balanceOf(tv) == MAX_TEST_FUND

    tv.release(cf.flip, {"from": addrs.INVESTOR})

    assert cf.flip.balanceOf(tv) == 0
    assert cf.flip.balanceOf(addrs.INVESTOR) == MAX_TEST_FUND

    # Assert that staking is no longer possible as the reference is wrong.
    # Let's say staking rewards are accrued
    cf.flip.transfer(tv, JUNK_INT, {"from": addrs.DEPLOYER})
    with reverts("Transaction reverted without a reason string"):
        tv.fundStateChainAccount(JUNK_INT, JUNK_INT, {"from": addrs.INVESTOR})
