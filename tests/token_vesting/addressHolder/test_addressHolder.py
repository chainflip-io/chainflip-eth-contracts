from consts import *
from brownie import reverts, chain
from shared_tests_tokenVesting import *


def test_reference_constructor(addrs, cf, AddressHolder):
    with reverts(REV_MSG_NZ_ADDR):
        addrs.DEPLOYER.deploy(AddressHolder, ZERO_ADDR, cf.stateChainGateway)

    with reverts(REV_MSG_NZ_ADDR):
        addrs.DEPLOYER.deploy(AddressHolder, NON_ZERO_ADDR, ZERO_ADDR)

    addressHolder = addrs.DEPLOYER.deploy(AddressHolder, addrs.DEPLOYER, NON_ZERO_ADDR)
    assert addressHolder.getGovernor() == addrs.DEPLOYER
    assert addressHolder.getReferenceAddress() == NON_ZERO_ADDR


def test_reference_transferGovernor(addrs, scGatewayAddrHolder):
    with reverts(REV_MSG_SCGREF_REV_GOV):
        scGatewayAddrHolder.transferGovernor(NON_ZERO_ADDR, {"from": addrs.BENEFICIARY})

    with reverts(REV_MSG_NZ_ADDR):
        scGatewayAddrHolder.transferGovernor(ZERO_ADDR, {"from": addrs.DEPLOYER})

    assert scGatewayAddrHolder.getGovernor() == addrs.DEPLOYER
    tx = scGatewayAddrHolder.transferGovernor(NON_ZERO_ADDR, {"from": addrs.DEPLOYER})
    assert tx.events["GovernorTransferred"][0].values() == [
        addrs.DEPLOYER,
        NON_ZERO_ADDR,
    ]
    assert scGatewayAddrHolder.getGovernor() == NON_ZERO_ADDR


def test_reference_updateReference(addrs, cf, scGatewayAddrHolder):
    with reverts(REV_MSG_SCGREF_REV_GOV):
        scGatewayAddrHolder.updateReferenceAddress(
            NON_ZERO_ADDR, {"from": addrs.BENEFICIARY}
        )

    with reverts(REV_MSG_NZ_ADDR):
        scGatewayAddrHolder.updateReferenceAddress(ZERO_ADDR, {"from": addrs.DEPLOYER})

    assert scGatewayAddrHolder.getReferenceAddress() == cf.stateChainGateway
    tx = scGatewayAddrHolder.updateReferenceAddress(
        NON_ZERO_ADDR, {"from": addrs.DEPLOYER}
    )
    assert tx.events["ReferenceAddressUpdated"][0].values() == [
        cf.stateChainGateway,
        NON_ZERO_ADDR,
    ]
    assert scGatewayAddrHolder.getReferenceAddress() == NON_ZERO_ADDR


def test_reference_release(addrs, cf, tokenVestingStaking, scGatewayAddrHolder):
    tv, _, _ = tokenVestingStaking

    assert cf.flip.balanceOf(addrs.BENEFICIARY) == 0

    tv.fundStateChainAccount(cf.flip, JUNK_INT, MAX_TEST_FUND, {"from": addrs.BENEFICIARY})

    chain.sleep(YEAR + QUARTER_YEAR)

    # Update the refernce to a wrong contract
    scGatewayAddrHolder.updateReferenceAddress(NON_ZERO_ADDR, {"from": addrs.DEPLOYER})

    # Mimic a return of funds from the state chain
    cf.flip.transfer(tv, MAX_TEST_FUND, {"from": addrs.DEPLOYER})

    assert cf.flip.balanceOf(tv) == MAX_TEST_FUND

    tv.release(cf.flip, {"from": addrs.BENEFICIARY})

    assert cf.flip.balanceOf(tv) == 0
    assert cf.flip.balanceOf(addrs.BENEFICIARY) == MAX_TEST_FUND

    # Assert that staking is no longer possible as the reference is wrong.
    # Let's say staking rewards are accrued
    cf.flip.transfer(tv, JUNK_INT, {"from": addrs.DEPLOYER})
    with reverts("Transaction reverted without a reason string"):
        tv.fundStateChainAccount(cf.flip, JUNK_INT, JUNK_INT, {"from": addrs.BENEFICIARY})
